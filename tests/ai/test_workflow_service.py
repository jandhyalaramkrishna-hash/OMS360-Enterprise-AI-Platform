"""
Tests for ai/integration/workflow_service.py — AIWorkflowService: the
Sprint 9 "Unified AI Workflow" that chains RAGSearchService -> MCPServer
-> AgentService -> AIChatService -> EvaluationService, using ONLY
already-built collaborators. Built with isolated, locally-constructed
instances of every collaborator (not the process-wide ai.dependencies
singletons), matching the pattern every other Sprint 4-8 service test
file already uses. tests/integration/test_ai_workflow_end_to_end.py
additionally exercises this against a fully-wired, production-shaped
assembly.
"""

import asyncio

import pytest

from ai.agents.agent_service import AgentService
from ai.agents.factory import AgentFactory
from ai.agents.messaging import AgentMessageBus
from ai.agents.orchestrator import AgentOrchestrator
from ai.core.exceptions import AIFeatureDisabledError, AIWorkflowInvalidRequestError
from ai.evals.accuracy import AccuracyScorer
from ai.evals.evaluation_service import EvaluationService
from ai.evals.latency import LatencyAnalyzer
from ai.evals.mock_dataset import MockEvalDataset
from ai.evals.reports import EvaluationReportBuilder
from ai.evals.runner import EvalRunner
from ai.integration.workflow_service import AIWorkflowService, WorkflowResult
from ai.mcp.config import MCPConfig
from ai.mcp.registry import MCPToolRegistry
from ai.mcp.router import MCPRequestRouter
from ai.mcp.server import MCPServer
from ai.mcp.tools.order_lookup_tool import OrderLookupTool
from ai.providers.mock_provider import MockAIProvider
from ai.providers.health import ProviderHealthChecker
from ai.providers.registry import ProviderRegistry
from ai.rag.context_builder import ContextBuilder
from ai.rag.config import RAGConfig
from ai.rag.document_parser import ParsedChunk
from ai.rag.mock_retriever import MockRetriever
from ai.rag.search_service import RAGSearchService
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.metrics import AIMetrics
from ai.services.ai_service import AIService
from ai.services.chat_service import AIChatService


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=True, rag_enabled=True, mcp_enabled=True, agents_enabled=True, evals_enabled=True,
        provider_name="mock", provider_api_key_configured=False,
        feature_flags={"rag_enabled": True, "mcp_enabled": True, "agents_enabled": True, "evals_enabled": True},
    )
    base.update(overrides)
    for key in ("rag_enabled", "mcp_enabled", "agents_enabled", "evals_enabled"):
        if key in overrides:
            base["feature_flags"] = {**base["feature_flags"], key: overrides[key]}
    return RuntimeConfiguration(**base)


def _build_workflow_service(**flag_overrides):
    runtime_config = _runtime_config(**flag_overrides)

    provider_registry = ProviderRegistry()
    provider_registry.register(MockAIProvider())
    ai_service = AIService(runtime_config, ValidationResult(), provider_registry)

    chunks = [ParsedChunk(chunk_id="c1", document_id="doc-1", content="refund policy details", source="faq", chunk_index=0)]
    search_service = RAGSearchService(
        MockRetriever(chunks), ContextBuilder(), ai_service,
        RAGConfig(default_top_k=5, max_context_chars=2000, chunk_max_chars=400),
    )

    tool_registry = MCPToolRegistry()
    tool_registry.register(OrderLookupTool())
    mcp_server = MCPServer(MCPRequestRouter(tool_registry, MCPConfig(tool_call_timeout_ms=5000)), ai_service)

    orchestrator = AgentOrchestrator()
    for agent in AgentFactory(AgentMessageBus()).create_all():
        orchestrator.register(agent)
    agent_service = AgentService(orchestrator, ai_service)

    metrics = AIMetrics()
    chat_service = AIChatService(ai_service, provider_registry, ProviderHealthChecker(), metrics)

    eval_runner = EvalRunner()
    report_builder = EvaluationReportBuilder(AccuracyScorer(), LatencyAnalyzer())
    evaluation_service = EvaluationService(eval_runner, report_builder, ai_service)
    mock_eval_dataset = MockEvalDataset()

    return AIWorkflowService(
        ai_service=ai_service,
        search_service=search_service,
        mcp_server=mcp_server,
        agent_service=agent_service,
        chat_service=chat_service,
        evaluation_service=evaluation_service,
        mock_eval_dataset=mock_eval_dataset,
    )


def test_run_returns_workflow_result_with_every_step_populated():
    service = _build_workflow_service()
    result = asyncio.run(service.run("ORD-1001", "refund policy"))

    assert isinstance(result, WorkflowResult)
    assert result.order_id == "ORD-1001"
    assert result.query == "refund policy"

    # RAG step
    assert result.rag_result is not None
    assert result.rag_result.context.chunk_count == 1

    # MCP step
    assert result.mcp_result is not None
    assert result.mcp_result.tool_name == "order_lookup"
    assert result.mcp_result.output["order_id"] == "ORD-1001"

    # Agent step - all six agents ran, in lifecycle order
    assert result.agent_history == [
        "order_agent", "inventory_agent", "kitchen_agent",
        "delivery_agent", "customer_support_agent", "analytics_agent",
    ]
    assert result.agent_data["order_id"] == "ORD-1001"
    assert result.agent_message_count > 0

    # Chat step
    assert result.chat_result is not None
    assert result.chat_result.provider == "mock"
    assert "[mock]" in result.chat_result.content

    # Evaluation step
    assert result.evaluation_summary is not None
    assert result.evaluation_summary.accuracy.total_cases == 6
    assert result.evaluation_summary.accuracy.accuracy == 1.0  # every mock echo contains its own keyword


def test_run_defaults_query_when_omitted():
    service = _build_workflow_service()
    result = asyncio.run(service.run("ORD-2002"))
    assert result.query == "status of order ORD-2002"


def test_run_rejects_blank_order_id():
    service = _build_workflow_service()
    with pytest.raises(AIWorkflowInvalidRequestError):
        asyncio.run(service.run("   "))


def test_run_rejects_non_string_order_id():
    service = _build_workflow_service()
    with pytest.raises(AIWorkflowInvalidRequestError):
        asyncio.run(service.run(None))


def test_run_propagates_disabled_rag_capability_from_the_first_step():
    service = _build_workflow_service(rag_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.run("ORD-3003"))


def test_run_propagates_disabled_mcp_capability():
    service = _build_workflow_service(mcp_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.run("ORD-4004"))


def test_run_propagates_disabled_agents_capability():
    service = _build_workflow_service(agents_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.run("ORD-5005"))


def test_run_propagates_disabled_evals_capability():
    service = _build_workflow_service(evals_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.run("ORD-6006"))


def test_run_propagates_master_ai_disabled():
    service = _build_workflow_service(ai_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.run("ORD-7007"))
