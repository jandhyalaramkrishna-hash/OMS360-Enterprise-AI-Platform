"""
AI Service Layer - Integration - Unified Platform Health Check (Sprint 9)
OMS-360 Enterprise Food Delivery Platform

PlatformHealthChecker aggregates health across every AI module built in
Sprints 1-8 into one report, reusing each module's own existing health
checker rather than reimplementing any of them: AIHealthService (Sprint
2, configuration-only), ProviderHealthChecker (Sprint 4, live probe),
MCPHealthChecker (Sprint 6, live probe), AgentHealthChecker (Sprint 7,
live probe), plus a snapshot of the existing AIMetrics counters (Sprint
2). This class performs no capability gating of its own and does not call
AIService.require_capability(...) - like AIHealthService itself, a health
report needs to work (and explain *why* something is unhealthy/disabled)
regardless of whether the corresponding feature flag is on, so this
endpoint stays reachable even when AI_ENABLED/RAG_ENABLED/etc. are false.
"""

from dataclasses import dataclass

from app.core.logging_config import get_logger

from ai.agents.health import AgentHealthChecker
from ai.agents.orchestrator import AgentOrchestrator
from ai.mcp.health import MCPHealthChecker
from ai.mcp.registry import MCPToolRegistry
from ai.metrics import AIMetrics, AIMetricsSnapshot
from ai.providers.health import ProviderHealthChecker
from ai.providers.registry import ProviderRegistry
from ai.services.health_service import AIHealthReport, AIHealthService

logger = get_logger("ai.integration.health")


@dataclass(frozen=True)
class PlatformHealthReport:
    """One consolidated view of every AI module's health. `overall_healthy`
    is true only if the runtime configuration has no validation errors AND
    every registered MCP tool AND every registered agent passed its live
    probe. Provider reachability is reported (`provider_results`) but does
    NOT gate `overall_healthy` - most providers are expected to be
    unconfigured (no API key), which AIHealthService itself already treats
    as a normal, non-error state, not a failure."""

    overall_healthy: bool
    runtime_health: AIHealthReport
    provider_results: list
    tool_results: list
    agent_results: list
    metrics: AIMetricsSnapshot


class PlatformHealthChecker:
    """Constructed via the shared
    ai.dependencies.get_platform_health_checker() singleton - not
    directly. Composes the existing per-module health checkers and
    registries rather than probing anything itself."""

    def __init__(
        self,
        ai_health_service: AIHealthService,
        provider_health_checker: ProviderHealthChecker,
        provider_registry: ProviderRegistry,
        mcp_health_checker: MCPHealthChecker,
        tool_registry: MCPToolRegistry,
        agent_health_checker: AgentHealthChecker,
        agent_orchestrator: AgentOrchestrator,
        ai_metrics: AIMetrics,
    ):
        self._ai_health_service = ai_health_service
        self._provider_health_checker = provider_health_checker
        self._provider_registry = provider_registry
        self._mcp_health_checker = mcp_health_checker
        self._tool_registry = tool_registry
        self._agent_health_checker = agent_health_checker
        self._agent_orchestrator = agent_orchestrator
        self._ai_metrics = ai_metrics
        logger.info("PlatformHealthChecker initialized")

    async def check(self) -> PlatformHealthReport:
        runtime_health = self._ai_health_service.check()

        providers = [self._provider_registry.get_provider(n) for n in self._provider_registry.list_providers()]
        provider_results = await self._provider_health_checker.check_all(providers)

        tools = [self._tool_registry.get_tool(n) for n in self._tool_registry.list_tools()]
        tool_results = await self._mcp_health_checker.check_all(tools)

        agents = [self._agent_orchestrator.get_agent(n) for n in self._agent_orchestrator.list_agents()]
        agent_results = await self._agent_health_checker.check_all(agents)

        overall_healthy = (
            runtime_health.healthy
            and all(result.healthy for result in tool_results)
            and all(result.healthy for result in agent_results)
        )

        logger.info(
            "Platform health check completed",
            extra={
                "ctx_overall_healthy": overall_healthy,
                "ctx_provider_count": len(provider_results),
                "ctx_tool_count": len(tool_results),
                "ctx_agent_count": len(agent_results),
            },
        )

        return PlatformHealthReport(
            overall_healthy=overall_healthy,
            runtime_health=runtime_health,
            provider_results=provider_results,
            tool_results=tool_results,
            agent_results=agent_results,
            metrics=self._ai_metrics.snapshot(),
        )
