"""
Sprint 9 - End-to-end integration test for the complete AI workflow.

Unlike tests/ai/test_workflow_service.py (which builds each collaborator
with a minimal, single-fixture setup to test AIWorkflowService's own
logic in isolation), this test assembles the FULL production wiring -
every real provider (via ProviderFactory), every real MCP tool (via
MCPToolFactory), every real mock agent (via AgentFactory), the real
MockEvalDataset - the same set ai/dependencies.py itself builds, just
under a locally-constructed, fully-enabled RuntimeConfiguration instead
of reading it from the environment (which defaults every capability to
disabled - see ai/runtime/config.py). This proves the actual production
assembly, not just AIWorkflowService's own branching logic, works end to
end. It exercises RAG retrieval over the real six built-in FAQ documents,
a real MCP order lookup among the real four registered tools, the real
six-agent mock lifecycle, a real MockAIProvider chat completion, and a
real evaluation pass over the built-in six-case dataset - all in-process,
zero network/database/Kafka access, matching every constraint every prior
sprint in this project already enforced.
"""

import asyncio

from ai.agents.agent_service import AgentService
from ai.agents.factory import AgentFactory
from ai.agents.messaging import AgentMessageBus
from ai.agents.orchestrator import AgentOrchestrator
from ai.evals.accuracy import AccuracyScorer
from ai.evals.evaluation_service import EvaluationService
from ai.evals.latency import LatencyAnalyzer
from ai.evals.mock_dataset import MockEvalDataset
from ai.evals.reports import EvaluationReportBuilder
from ai.evals.runner import EvalRunner
from ai.integration.health import PlatformHealthChecker
from ai.integration.workflow_service import AGENT_SEQUENCE, AIWorkflowService
from ai.mcp.config import MCPConfig
from ai.mcp.health import MCPHealthChecker
from ai.mcp.registry import MCPToolRegistry
from ai.mcp.router import MCPRequestRouter
from ai.mcp.server import MCPServer
from ai.mcp.tools.factory import MCPToolFactory
from ai.metrics import AIMetrics
from ai.providers.factory import ProviderFactory
from ai.providers.health import ProviderHealthChecker
from ai.rag.context_builder import ContextBuilder
from ai.rag.config import RAGConfig
from ai.rag.document_loader import MockDocumentLoader
from ai.rag.document_parser import SimpleDocumentParser
from ai.rag.knowledge_base import KnowledgeBase
from ai.rag.mock_retriever import MockRetriever
from ai.rag.search_service import RAGSearchService
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.ai_service import AIService
from ai.services.chat_service import AIChatService
from ai.services.health_service import AIHealthService


def _fully_enabled_runtime_config() -> RuntimeConfiguration:
    flags = {"rag_enabled": True, "mcp_enabled": True, "agents_enabled": True, "evals_enabled": True}
    return RuntimeConfiguration(
        ai_enabled=True, rag_enabled=True, mcp_enabled=True, agents_enabled=True, evals_enabled=True,
        provider_name="mock", provider_api_key_configured=False, feature_flags=flags,
    )


class _Platform:
    """Assembles the full production-shaped AI platform, mirroring
    ai/dependencies.py's own wiring exactly, but with a fully-enabled
    RuntimeConfiguration and fresh, test-local instances of everything -
    so this test never touches (and cannot be affected by, or affect) the
    process-wide ai.dependencies singletons the rest of the suite uses."""

    def __init__(self):
        runtime_config = _fully_enabled_runtime_config()
        validation = ValidationResult()

        self.provider_registry = ProviderFactory.build_registry()
        self.ai_service = AIService(runtime_config, validation, self.provider_registry)
        self.ai_health_service = AIHealthService(runtime_config, validation, self.provider_registry)

        rag_config = RAGConfig(default_top_k=5, max_context_chars=2000, chunk_max_chars=400)
        knowledge_base = KnowledgeBase()
        for document in MockDocumentLoader().load():
            knowledge_base.add_document(document)
        parser = SimpleDocumentParser(chunk_max_chars=rag_config.chunk_max_chars)
        chunks = []
        for document in knowledge_base.all_documents():
            chunks.extend(parser.parse(document))
        self.search_service = RAGSearchService(
            MockRetriever(chunks), ContextBuilder(), self.ai_service, rag_config
        )

        self.tool_registry = MCPToolRegistry()
        for tool in MCPToolFactory.create_all():
            self.tool_registry.register(tool)
        mcp_router = MCPRequestRouter(self.tool_registry, MCPConfig(tool_call_timeout_ms=5000))
        self.mcp_server = MCPServer(mcp_router, self.ai_service)
        self.mcp_health_checker = MCPHealthChecker()

        self.agent_orchestrator = AgentOrchestrator()
        message_bus = AgentMessageBus()
        for agent in AgentFactory(message_bus).create_all():
            self.agent_orchestrator.register(agent)
        self.agent_service = AgentService(self.agent_orchestrator, self.ai_service)
        from ai.agents.health import AgentHealthChecker
        self.agent_health_checker = AgentHealthChecker()

        self.ai_metrics = AIMetrics()
        self.provider_health_checker = ProviderHealthChecker()
        self.chat_service = AIChatService(
            self.ai_service, self.provider_registry, self.provider_health_checker, self.ai_metrics
        )

        self.mock_eval_dataset = MockEvalDataset()
        self.evaluation_service = EvaluationService(
            EvalRunner(), EvaluationReportBuilder(AccuracyScorer(), LatencyAnalyzer()), self.ai_service
        )

        self.workflow_service = AIWorkflowService(
            ai_service=self.ai_service,
            search_service=self.search_service,
            mcp_server=self.mcp_server,
            agent_service=self.agent_service,
            chat_service=self.chat_service,
            evaluation_service=self.evaluation_service,
            mock_eval_dataset=self.mock_eval_dataset,
        )

        self.platform_health_checker = PlatformHealthChecker(
            ai_health_service=self.ai_health_service,
            provider_health_checker=self.provider_health_checker,
            provider_registry=self.provider_registry,
            mcp_health_checker=self.mcp_health_checker,
            tool_registry=self.tool_registry,
            agent_health_checker=self.agent_health_checker,
            agent_orchestrator=self.agent_orchestrator,
            ai_metrics=self.ai_metrics,
        )


def test_full_production_wiring_runs_the_complete_workflow_end_to_end():
    platform = _Platform()

    result = asyncio.run(platform.workflow_service.run("ORD-END-TO-END-1", "what is your refund policy?"))

    # RAG actually retrieved from the real six built-in FAQ documents.
    assert result.rag_result.chunks, "expected RAG to retrieve at least one real FAQ chunk"
    assert result.rag_result.context.chunk_count > 0

    # MCP actually called the real order_lookup tool among 4 registered tools.
    assert len(platform.tool_registry.list_tools()) == 4
    assert result.mcp_result.tool_name == "order_lookup"
    assert result.mcp_result.output["order_id"] == "ORD-END-TO-END-1"
    assert result.mcp_result.output["status"] in (
        "placed", "confirmed", "preparing", "ready_for_pickup", "out_for_delivery", "delivered",
    )

    # All 6 real mock agents ran, in lifecycle order, and exchanged messages.
    assert result.agent_history == list(AGENT_SEQUENCE)
    assert result.agent_message_count == 4  # order->kitchen, inventory->order, kitchen->delivery, delivery->support

    # The chat step actually called MockAIProvider and got a real result.
    assert result.chat_result.provider == "mock"
    assert result.chat_result.is_mock is True
    assert result.chat_result.content.startswith("[mock]")

    # The evaluation step actually scored all 6 built-in mock cases.
    assert result.evaluation_summary.accuracy.total_cases == 6
    assert result.evaluation_summary.accuracy.passed_cases == 6
    assert result.evaluation_summary.latency.sample_count == 6

    # AIMetrics actually recorded activity from the chat calls this
    # workflow made (one in step 4, six more inside the evaluation step).
    metrics_snapshot = platform.ai_metrics.snapshot()
    assert metrics_snapshot.request_count == 7  # 1 (chat step) + 6 (eval cases)
    assert metrics_snapshot.response_count == 7


def test_full_production_wiring_runs_multiple_orders_independently():
    platform = _Platform()

    result_a = asyncio.run(platform.workflow_service.run("ORD-AAA"))
    result_b = asyncio.run(platform.workflow_service.run("ORD-BBB"))

    assert result_a.order_id == "ORD-AAA"
    assert result_b.order_id == "ORD-BBB"
    assert result_a.mcp_result.output["order_id"] == "ORD-AAA"
    assert result_b.mcp_result.output["order_id"] == "ORD-BBB"
    # Deterministic mock data - different order ids may legitimately land
    # on the same or different statuses, but each result is internally
    # consistent with its own order id.
    assert result_a.agent_data["order_id"] == "ORD-AAA"
    assert result_b.agent_data["order_id"] == "ORD-BBB"


def test_platform_health_check_reports_the_full_production_assembly_as_healthy():
    platform = _Platform()

    report = asyncio.run(platform.platform_health_checker.check())

    assert report.overall_healthy is True
    assert len(report.tool_results) == 4
    assert len(report.agent_results) == 6
    assert len(report.provider_results) == 5  # openai, anthropic, azure_openai, ollama, mock
    assert all(r.healthy for r in report.tool_results)
    assert all(r.healthy for r in report.agent_results)


def test_platform_health_check_and_workflow_share_the_same_underlying_registrations():
    """Sanity check that ai.integration.health and
    ai.integration.workflow_service, when built over the same
    collaborators (as ai/dependencies.py itself does), agree on which
    tools/agents exist - no drift between the two Sprint 9 entry points."""
    platform = _Platform()

    report = asyncio.run(platform.platform_health_checker.check())
    workflow_result = asyncio.run(platform.workflow_service.run("ORD-CONSISTENCY-CHECK"))

    tool_names_from_health = {r.tool_name for r in report.tool_results}
    assert workflow_result.mcp_result.tool_name in tool_names_from_health

    agent_names_from_health = {r.agent_name for r in report.agent_results}
    assert set(workflow_result.agent_history) == agent_names_from_health
