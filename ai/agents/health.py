"""
AI Service Layer - Agents - Health Check (Sprint 7)
OMS-360 Enterprise Food Delivery Platform

AgentHealthChecker is a live probe that actually calls each agent's
run() with a harmless probe AgentContext, mirroring MCPHealthChecker
(Sprint 6). Unlike MCP tools, agents have no declared input_schema, so
the probe context is a single, fixed, agent-agnostic AgentContext rather
than one built from per-agent required fields - every mock agent is
written to tolerate missing context.data keys via `.get(..., default)`,
so this generic probe is safe to run against any of them.
"""

from dataclasses import dataclass

from app.core.logging_config import get_logger

from ai.agents.base import AgentContext

logger = get_logger("ai.agents.health")

_PROBE_INPUT = "healthcheck-probe"


@dataclass(frozen=True)
class AgentHealthResult:
    agent_name: str
    healthy: bool
    error: str = None


class AgentHealthChecker:
    async def check(self, agent) -> AgentHealthResult:
        try:
            await agent.run(AgentContext(input=_PROBE_INPUT))
            return AgentHealthResult(agent_name=agent.name, healthy=True)
        except Exception as exc:  # noqa: BLE001 - a failing probe must report unhealthy, not crash the checker
            logger.warning("Agent health probe failed", extra={"ctx_agent_name": agent.name, "ctx_error": str(exc)})
            return AgentHealthResult(agent_name=agent.name, healthy=False, error=str(exc))

    async def check_all(self, agents: list) -> list:
        return [await self.check(agent) for agent in agents]
