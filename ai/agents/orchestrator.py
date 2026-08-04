"""
AI Service Layer - Agents - Orchestrator
OMS-360 Enterprise Food Delivery Platform

Minimal, sequential multi-agent orchestrator: runs a named list of
registered agents in order, each receiving the AgentContext produced by
the previous one. No agents are registered by default - which agents
exist and what they're allowed to do is a later, separate decision.

Sprint 7 change: agent bookkeeping (register/lookup/list) now delegates
to an injected AgentRegistry (defaulting to a fresh one if not supplied)
instead of maintaining its own dict, so there is exactly one place that
answers "which agents exist" - consistent with the "one shared
collaborator" pattern DEC-0017/0018/0019 established for
ProviderRegistry/MCPToolRegistry. This is a behavior-preserving
refactor: AgentOrchestrator() with no arguments still works exactly as
before, and tests/ai/test_agents.py (Sprint 1) passes unmodified. This
sprint also adds exception wrapping around an agent's run() so an
unexpected failure surfaces as AIAgentExecutionError rather than an
uncaught, unclassified exception - mirroring how MCPRequestRouter wraps
unexpected tool failures (Sprint 6).
"""

from app.core.logging_config import get_logger

from ai.agents.base import AgentContext
from ai.agents.registry import AgentRegistry
from ai.core.exceptions import AIAgentExecutionError, AIServiceError

logger = get_logger("ai.agents")


class AgentOrchestrator:
    def __init__(self, registry: AgentRegistry = None):
        self._registry = registry or AgentRegistry()
        logger.info(
            "AgentOrchestrator initialized",
            extra={"ctx_agent_count": len(self._registry.list_agents())},
        )

    def register(self, agent) -> None:
        self._registry.register(agent)

    def list_agents(self) -> list:
        return self._registry.list_agents()

    def get_agent(self, name: str):
        """Sprint 9 addition: a plain passthrough to the underlying
        AgentRegistry, mirroring MCPToolRegistry.get_tool(). Added so
        callers that need the actual agent object (e.g.
        ai.integration.health.PlatformHealthChecker, which live-probes
        every registered agent) don't need their own reference to the
        registry - the orchestrator remains the one place that answers
        both "which agents exist" (list_agents) and "give me one of them"
        (get_agent). Raises AIAgentNotRegisteredError(name) for an unknown
        name, same as AgentRegistry.get_agent()."""
        return self._registry.get_agent(name)

    async def run_sequence(self, agent_names: list, context: AgentContext) -> AgentContext:
        for name in agent_names:
            agent = self._registry.get_agent(name)  # raises AIAgentNotRegisteredError(name)
            logger.info("Running agent", extra={"ctx_agent_name": name})
            try:
                context = await agent.run(context)
            except AIServiceError:
                raise
            except Exception as exc:  # noqa: BLE001 - one agent's bug must not crash the whole run silently
                raise AIAgentExecutionError(name, str(exc)) from exc
            context.history.append(name)
        return context
