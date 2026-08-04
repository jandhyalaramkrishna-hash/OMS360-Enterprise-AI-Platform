"""
Tests for ai/agents/health.py — AgentHealthChecker: a live probe that
actually calls each agent's run() with a harmless probe context.
"""

import asyncio

from ai.agents.base import AgentBase, AgentContext
from ai.agents.health import AgentHealthChecker, AgentHealthResult
from ai.agents.messaging import AgentMessageBus
from ai.agents.factory import AgentFactory


class _AlwaysFailsAgent(AgentBase):
    name = "always_fails"

    async def run(self, context: AgentContext) -> AgentContext:
        raise RuntimeError("simulated agent failure")


def test_check_reports_healthy_for_a_working_agent():
    checker = AgentHealthChecker()
    agent = AgentFactory(AgentMessageBus()).create_all()[0]
    result = asyncio.run(checker.check(agent))
    assert isinstance(result, AgentHealthResult)
    assert result.healthy is True
    assert result.error is None


def test_check_reports_unhealthy_when_agent_raises():
    checker = AgentHealthChecker()
    result = asyncio.run(checker.check(_AlwaysFailsAgent()))
    assert result.healthy is False
    assert "simulated agent failure" in result.error


def test_check_all_covers_every_agent():
    checker = AgentHealthChecker()
    agents = AgentFactory(AgentMessageBus()).create_all()
    results = asyncio.run(checker.check_all(agents))
    assert {r.agent_name for r in results} == {a.name for a in agents}
    assert all(r.healthy for r in results)
