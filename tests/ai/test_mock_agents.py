"""
Tests for ai/agents/mock_agents/* — each mock agent's deterministic
output shape, variation across different order ids, and the mock
messages it publishes.
"""

import asyncio

from ai.agents.base import AgentContext
from ai.agents.messaging import AgentMessageBus
from ai.agents.mock_agents.analytics_agent import AnalyticsAgent
from ai.agents.mock_agents.customer_support_agent import CustomerSupportAgent
from ai.agents.mock_agents.delivery_agent import DeliveryAgent
from ai.agents.mock_agents.inventory_agent import InventoryAgent
from ai.agents.mock_agents.kitchen_agent import KitchenAgent
from ai.agents.mock_agents.order_agent import OrderAgent


def _context(order_id="ORD-1"):
    return AgentContext(input=order_id, data={"order_id": order_id})


def test_order_agent_produces_deterministic_result_and_publishes_message():
    bus = AgentMessageBus()
    agent = OrderAgent(bus)
    context = asyncio.run(agent.run(_context("ORD-1")))

    result = context.data["order_agent_result"]
    assert result["order_id"] == "ORD-1"
    assert result["status"] in (
        "received", "confirmed", "preparing", "ready", "out_for_delivery", "delivered",
    )
    assert result["is_mock"] is True

    assert len(context.messages) == 1
    message = context.messages[0]
    assert message.sender == "order_agent"
    assert message.recipient == "kitchen_agent"


def test_order_agent_is_deterministic_for_the_same_id():
    bus = AgentMessageBus()
    r1 = asyncio.run(OrderAgent(bus).run(_context("ORD-42")))
    r2 = asyncio.run(OrderAgent(bus).run(_context("ORD-42")))
    assert r1.data["order_agent_result"]["status"] == r2.data["order_agent_result"]["status"]


def test_inventory_agent_result_shape_and_message():
    bus = AgentMessageBus()
    context = asyncio.run(InventoryAgent(bus).run(_context("ORD-2")))
    result = context.data["inventory_agent_result"]
    assert result["order_id"] == "ORD-2"
    assert isinstance(result["in_stock"], bool)
    assert 0 <= result["quantity"] <= 100
    assert context.messages[0].recipient == "order_agent"


def test_kitchen_agent_result_shape_and_message():
    bus = AgentMessageBus()
    context = asyncio.run(KitchenAgent(bus).run(_context("ORD-3")))
    result = context.data["kitchen_agent_result"]
    assert 5 <= result["prep_time_minutes"] <= 30
    assert context.messages[0].recipient == "delivery_agent"


def test_delivery_agent_result_shape_and_message():
    bus = AgentMessageBus()
    context = asyncio.run(DeliveryAgent(bus).run(_context("ORD-4")))
    result = context.data["delivery_agent_result"]
    assert result["driver_name"] in ("Alex", "Jordan", "Sam", "Taylor", "Morgan")
    assert 10 <= result["eta_minutes"] <= 45
    assert context.messages[0].recipient == "customer_support_agent"


def test_customer_support_agent_with_no_inbound_messages():
    bus = AgentMessageBus()
    context = asyncio.run(CustomerSupportAgent(bus).run(_context("ORD-5")))
    result = context.data["customer_support_agent_result"]
    assert result["latest_update"] == "no_updates_yet"
    assert result["messages_received"] == 0


def test_customer_support_agent_reads_latest_inbound_message():
    bus = AgentMessageBus()
    context = _context("ORD-6")
    bus.publish(context, "delivery_agent", "customer_support_agent", "delivery_dispatched")
    context = asyncio.run(CustomerSupportAgent(bus).run(context))
    result = context.data["customer_support_agent_result"]
    assert result["latest_update"] == "delivery_dispatched"
    assert result["messages_received"] == 1


def test_analytics_agent_summarizes_history_and_messages():
    bus = AgentMessageBus()
    context = _context("ORD-7")
    context.history = ["order_agent", "kitchen_agent"]
    bus.publish(context, "a", "b", "m1")
    context = asyncio.run(AnalyticsAgent(bus).run(context))
    result = context.data["analytics_agent_result"]
    assert result["agents_run"] == 2
    assert result["messages_exchanged"] == 1


def test_agents_fall_back_to_context_input_when_order_id_missing():
    bus = AgentMessageBus()
    context = AgentContext(input="FALLBACK-ID")
    context = asyncio.run(OrderAgent(bus).run(context))
    assert context.data["order_agent_result"]["order_id"] == "FALLBACK-ID"
