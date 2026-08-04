"""
AI Service Layer - Agents - Agent Service (Sprint 7)
OMS-360 Enterprise Food Delivery Platform

AgentService is a thin, capability-gated layer over AgentOrchestrator,
mirroring the MCPRequestRouter/MCPServer split from Sprint 6:
AgentOrchestrator owns pure execution mechanics (register/list/run a
sequence) and has no knowledge of enablement; AgentService adds the
existing AIService.require_capability("agents_enabled") gate on top of
it. This keeps AgentOrchestrator usable on its own (as
tests/ai/test_agents.py already does, unmodified) while giving callers a
policy-enforcing entry point.
"""

from ai.agents.base import AgentContext
from ai.agents.orchestrator import AgentOrchestrator
from ai.services.ai_service import AIService

_CAPABILITY = "agents_enabled"


class AgentService:
    def __init__(self, orchestrator: AgentOrchestrator, ai_service: AIService):
        self._orchestrator = orchestrator
        self._ai_service = ai_service

    async def run(self, agent_names: list, context: AgentContext) -> AgentContext:
        self._ai_service.require_capability(_CAPABILITY)
        return await self._orchestrator.run_sequence(agent_names, context)

    def list_agents(self) -> list:
        self._ai_service.require_capability(_CAPABILITY)
        return self._orchestrator.list_agents()
