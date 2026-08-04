"""
Tests for ai/integration/health.py — PlatformHealthChecker: aggregates
health across every AI module, reusing each module's own existing health
checker. Built with isolated, locally-constructed instances (not the
process-wide ai.dependencies singletons), matching the pattern every
other Sprint 4-8 service test file (test_mcp_server.py,
test_search_service.py, test_evaluation_service.py, ...) already uses.
"""

import asyncio

from ai.agents.factory import AgentFactory
from ai.agents.health import AgentHealthChecker
from ai.agents.messaging import AgentMessageBus
from ai.agents.orchestrator import AgentOrchestrator
from ai.integration.health import PlatformHealthChecker, PlatformHealthReport
from ai.mcp.health import MCPHealthChecker
from ai.mcp.registry import MCPToolRegistry
from ai.mcp.tools.factory import MCPToolFactory
from ai.metrics import AIMetrics
from ai.providers.health import ProviderHealthChecker
from ai.providers.mock_provider import MockAIProvider
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.health_service import AIHealthService


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=True, rag_enabled=True, mcp_enabled=True, agents_enabled=True, evals_enabled=True,
        provider_name="mock", provider_api_key_configured=False,
        feature_flags={"rag_enabled": True, "mcp_enabled": True, "agents_enabled": True, "evals_enabled": True},
    )
    base.update(overrides)
    return RuntimeConfiguration(**base)


def _make_checker(validation=None):
    provider_registry = ProviderRegistry()
    provider_registry.register(MockAIProvider())

    tool_registry = MCPToolRegistry()
    for tool in MCPToolFactory.create_all():
        tool_registry.register(tool)

    orchestrator = AgentOrchestrator()
    for agent in AgentFactory(AgentMessageBus()).create_all():
        orchestrator.register(agent)

    return PlatformHealthChecker(
        ai_health_service=AIHealthService(_runtime_config(), validation or ValidationResult(), provider_registry),
        provider_health_checker=ProviderHealthChecker(),
        provider_registry=provider_registry,
        mcp_health_checker=MCPHealthChecker(),
        tool_registry=tool_registry,
        agent_health_checker=AgentHealthChecker(),
        agent_orchestrator=orchestrator,
        ai_metrics=AIMetrics(),
    )


def test_check_returns_platform_health_report():
    checker = _make_checker()
    report = asyncio.run(checker.check())
    assert isinstance(report, PlatformHealthReport)


def test_check_reports_overall_healthy_true_when_everything_is_healthy():
    checker = _make_checker()
    report = asyncio.run(checker.check())
    assert report.overall_healthy is True
    assert report.runtime_health.healthy is True


def test_check_probes_every_registered_mcp_tool():
    checker = _make_checker()
    report = asyncio.run(checker.check())
    tool_names = {r.tool_name for r in report.tool_results}
    assert tool_names == set(MCPToolFactory.known_tool_names())
    assert all(r.healthy for r in report.tool_results)


def test_check_probes_every_registered_agent():
    checker = _make_checker()
    report = asyncio.run(checker.check())
    agent_names = {r.agent_name for r in report.agent_results}
    assert agent_names == set(AgentFactory(AgentMessageBus()).known_agent_names())
    assert all(r.healthy for r in report.agent_results)


def test_check_probes_every_registered_provider():
    checker = _make_checker()
    report = asyncio.run(checker.check())
    provider_names = {r.provider for r in report.provider_results}
    assert "mock" in provider_names
    mock_result = next(r for r in report.provider_results if r.provider == "mock")
    assert mock_result.configured is True
    assert mock_result.reachable is True


def test_check_overall_healthy_is_false_when_runtime_configuration_has_errors():
    validation = ValidationResult()
    validation.errors.append("simulated configuration error")
    checker = _make_checker(validation=validation)
    report = asyncio.run(checker.check())
    assert report.runtime_health.healthy is False
    assert report.overall_healthy is False
    # A configuration error does not stop live probing of tools/agents -
    # this is a diagnostic report, not a gate.
    assert len(report.tool_results) > 0
    assert len(report.agent_results) > 0


def test_check_includes_a_metrics_snapshot():
    metrics = AIMetrics()
    metrics.record_request()
    metrics.record_response(token_usage=5)

    provider_registry = ProviderRegistry()
    provider_registry.register(MockAIProvider())
    tool_registry = MCPToolRegistry()
    for tool in MCPToolFactory.create_all():
        tool_registry.register(tool)
    orchestrator = AgentOrchestrator()
    for agent in AgentFactory(AgentMessageBus()).create_all():
        orchestrator.register(agent)

    checker = PlatformHealthChecker(
        ai_health_service=AIHealthService(_runtime_config(), ValidationResult(), provider_registry),
        provider_health_checker=ProviderHealthChecker(),
        provider_registry=provider_registry,
        mcp_health_checker=MCPHealthChecker(),
        tool_registry=tool_registry,
        agent_health_checker=AgentHealthChecker(),
        agent_orchestrator=orchestrator,
        ai_metrics=metrics,
    )
    report = asyncio.run(checker.check())
    assert report.metrics.request_count == 1
    assert report.metrics.response_count == 1
    assert report.metrics.token_usage_total == 5
