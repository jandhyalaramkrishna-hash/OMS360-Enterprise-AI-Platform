"""
Tests for ai/agents/factory.py — AgentFactory: known_agent_names() /
create_all(), mirroring MCPToolFactory's test shape.
"""

from ai.agents.base import AgentBase
from ai.agents.factory import AgentFactory
from ai.agents.messaging import AgentMessageBus
from ai.agents.mock_agents.analytics_agent import AnalyticsAgent
from ai.agents.mock_agents.customer_support_agent import CustomerSupportAgent
from ai.agents.mock_agents.delivery_agent import DeliveryAgent
from ai.agents.mock_agents.inventory_agent import InventoryAgent
from ai.agents.mock_agents.kitchen_agent import KitchenAgent
from ai.agents.mock_agents.order_agent import OrderAgent

_EXPECTED_NAMES = sorted([
    "order_agent", "inventory_agent", "kitchen_agent",
    "delivery_agent", "customer_support_agent", "analytics_agent",
])

_EXPECTED_CLASSES = {
    OrderAgent, InventoryAgent, KitchenAgent, DeliveryAgent, CustomerSupportAgent, AnalyticsAgent,
}


def test_known_agent_names_sorted_and_complete():
    factory = AgentFactory(AgentMessageBus())
    assert factory.known_agent_names() == _EXPECTED_NAMES


def test_create_all_returns_six_agent_instances():
    factory = AgentFactory(AgentMessageBus())
    agents = factory.create_all()
    assert len(agents) == 6
    assert all(isinstance(a, AgentBase) for a in agents)
    assert {type(a) for a in agents} == _EXPECTED_CLASSES


def test_create_all_returns_fresh_instances_per_call():
    factory = AgentFactory(AgentMessageBus())
    first = factory.create_all()
    second = factory.create_all()
    for a, b in zip(first, second):
        assert a is not b


def test_all_agents_share_the_injected_message_bus():
    bus = AgentMessageBus()
    factory = AgentFactory(bus)
    for agent in factory.create_all():
        assert agent._message_bus is bus
