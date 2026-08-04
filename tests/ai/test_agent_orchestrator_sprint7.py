"""
Sprint 7 tests for ai/agents/orchestrator.py — AgentOrchestrator running
the real six mock agents end to end, and its Sprint 7 exception-wrapping
behavior. tests/ai/test_agents.py (Sprint 1) already covers the
orchestrator's basic sequencing/registry behavior with local fixtures and
is left unmodified; these tests specifically exercise what Sprint 7 added.
"""

import asyncio

import pytest

from ai.agents.base import AgentBase, AgentContext
from ai.agents.factory import AgentFactory
from ai.agents.messaging import AgentMessageBus
from ai.agents.orchestrator import AgentOrchestrator
from ai.core.exceptions import AIAgentExecutionError


class _BoomAgent(AgentBase):
    name = "boom"

    async def run(self, context: AgentContext) -> AgentContext:
        raise RuntimeError("kaboom")


def _full_orchestrator():
    orchestrator = AgentOrchestrator()
    for agent in AgentFactory(AgentMessageBus()).create_all():
        orchestrator.register(agent)
    return orchestrator


def test_full_agent_sequence_runs_in_order_and_exchanges_messages():
    orchestrator = _full_orchestrator()
    context = AgentContext(input="ORD-99", data={"order_id": "ORD-99"})

    result = asyncio.run(orchestrator.run_sequence(
        ["order_agent", "inventory_agent", "kitchen_agent", "delivery_agent",
         "customer_support_agent", "analytics_agent"],
        context,
    ))

    assert result.history == [
        "order_agent", "inventory_agent", "kitchen_agent",
        "delivery_agent", "customer_support_agent", "analytics_agent",
    ]
    assert len(result.messages) == 4  # order->kitchen, inventory->order, kitchen->delivery, delivery->support
    # AnalyticsAgent reads context.history from *inside* its own run() - the
    # orchestrator appends each agent's name to history only after run()
    # returns, so history holds the 5 agents that ran before it, not itself.
    assert result.data["analytics_agent_result"]["agents_run"] == 5
    assert result.data["analytics_agent_result"]["messages_exchanged"] == 4


def test_orchestrator_wraps_unexpected_agent_exception():
    orchestrator = AgentOrchestrator()
    orchestrator.register(_BoomAgent())
    with pytest.raises(AIAgentExecutionError):
        asyncio.run(orchestrator.run_sequence(["boom"], AgentContext(input="hi")))


def test_orchestrator_constructor_accepts_no_arguments_still():
    # Backward-compatibility guarantee for tests/ai/test_agents.py (Sprint 1).
    orchestrator = AgentOrchestrator()
    assert orchestrator.list_agents() == []
