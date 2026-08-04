"""
Sprint 9 test for the one additive method Sprint 9 added to
ai/agents/orchestrator.py — AgentOrchestrator.get_agent(name), a plain
passthrough to the underlying AgentRegistry added so
ai.integration.health.PlatformHealthChecker can fetch actual agent
objects (not just names) for its live probes.
"""

import pytest

from ai.agents.base import AgentBase, AgentContext
from ai.agents.orchestrator import AgentOrchestrator
from ai.core.exceptions import AIAgentNotRegisteredError


class _EchoAgent(AgentBase):
    name = "echo_agent"

    async def run(self, context: AgentContext) -> AgentContext:
        return context


def test_get_agent_returns_the_registered_agent():
    orchestrator = AgentOrchestrator()
    agent = _EchoAgent()
    orchestrator.register(agent)
    assert orchestrator.get_agent("echo_agent") is agent


def test_get_agent_raises_for_unknown_name():
    orchestrator = AgentOrchestrator()
    with pytest.raises(AIAgentNotRegisteredError):
        orchestrator.get_agent("nonexistent")
