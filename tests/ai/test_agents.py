"""
Tests for ai/agents — AgentOrchestrator sequential run behavior.
"""

import asyncio

import pytest

from ai.agents.base import AgentBase, AgentContext
from ai.agents.orchestrator import AgentOrchestrator
from ai.core.exceptions import AIAgentNotRegisteredError


class _UppercaseAgent(AgentBase):
    name = "uppercase"

    async def run(self, context: AgentContext) -> AgentContext:
        context.data["result"] = context.input.upper()
        return context


class _ReverseAgent(AgentBase):
    name = "reverse"

    async def run(self, context: AgentContext) -> AgentContext:
        context.data["result"] = context.data.get("result", context.input)[::-1]
        return context


def test_run_sequence_with_no_agents_registered_raises():
    orchestrator = AgentOrchestrator()
    with pytest.raises(AIAgentNotRegisteredError):
        asyncio.run(orchestrator.run_sequence(["anything"], AgentContext(input="hi")))


def test_run_sequence_with_unregistered_agent_name_raises():
    orchestrator = AgentOrchestrator()
    orchestrator.register(_UppercaseAgent())
    with pytest.raises(AIAgentNotRegisteredError):
        asyncio.run(orchestrator.run_sequence(["not_registered"], AgentContext(input="hi")))


def test_run_sequence_chains_agents_in_order():
    orchestrator = AgentOrchestrator()
    orchestrator.register(_UppercaseAgent())
    orchestrator.register(_ReverseAgent())

    result = asyncio.run(
        orchestrator.run_sequence(["uppercase", "reverse"], AgentContext(input="abc"))
    )

    assert result.data["result"] == "CBA"
    assert result.history == ["uppercase", "reverse"]


def test_list_agents_sorted():
    orchestrator = AgentOrchestrator()
    orchestrator.register(_ReverseAgent())
    orchestrator.register(_UppercaseAgent())
    assert orchestrator.list_agents() == ["reverse", "uppercase"]
