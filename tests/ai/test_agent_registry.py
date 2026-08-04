"""
Tests for ai/agents/registry.py — AgentRegistry: register/look-up/list,
mirroring MCPToolRegistry's test shape.
"""

import pytest

from ai.agents.base import AgentBase, AgentContext
from ai.agents.registry import AgentRegistry
from ai.core.exceptions import AIAgentNotRegisteredError


class _EchoAgent(AgentBase):
    name = "echo"

    async def run(self, context: AgentContext) -> AgentContext:
        return context


class _OtherAgent(AgentBase):
    name = "other"

    async def run(self, context: AgentContext) -> AgentContext:
        return context


def test_registry_starts_empty():
    registry = AgentRegistry()
    assert registry.list_agents() == []


def test_register_and_get_agent():
    registry = AgentRegistry()
    agent = _EchoAgent()
    registry.register(agent)
    assert registry.get_agent("echo") is agent


def test_get_unregistered_agent_raises():
    registry = AgentRegistry()
    with pytest.raises(AIAgentNotRegisteredError):
        registry.get_agent("does_not_exist")


def test_registering_same_name_twice_overwrites():
    registry = AgentRegistry()
    first = _EchoAgent()
    second = _EchoAgent()
    registry.register(first)
    registry.register(second)
    assert registry.get_agent("echo") is second


def test_list_agents_sorted():
    registry = AgentRegistry()
    registry.register(_OtherAgent())
    registry.register(_EchoAgent())
    assert registry.list_agents() == ["echo", "other"]
