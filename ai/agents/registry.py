"""
AI Service Layer - Agents - Agent Registry (Sprint 7)
OMS-360 Enterprise Food Delivery Platform

Extracted from AgentOrchestrator's previously-internal `_agents` dict
(Sprint 1) into its own class, mirroring MCPToolRegistry (Sprint 1/6) and
ProviderRegistry (Sprint 2): a single, explicit "which agents exist"
collaborator that AgentOrchestrator composes rather than re-implements.
See DEC-0020 for why this extraction was made rather than building a
second, parallel agent registry alongside the orchestrator's own dict.
"""

from app.core.logging_config import get_logger

from ai.core.exceptions import AIAgentNotRegisteredError

logger = get_logger("ai.agents.registry")


class AgentRegistry:
    def __init__(self):
        self._agents = {}
        logger.info("AgentRegistry initialized", extra={"ctx_agent_count": 0})

    def register(self, agent) -> None:
        if agent.name in self._agents:
            logger.warning("Overwriting already-registered agent", extra={"ctx_agent_name": agent.name})
        self._agents[agent.name] = agent
        logger.info("Agent registered", extra={"ctx_agent_name": agent.name})

    def get_agent(self, name: str):
        if name not in self._agents:
            raise AIAgentNotRegisteredError(name)
        return self._agents[name]

    def list_agents(self) -> list:
        return sorted(self._agents.keys())
