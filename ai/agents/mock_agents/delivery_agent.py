"""
AI Service Layer - Agents - Mock Agents - Delivery Agent (Sprint 7)
OMS-360 Enterprise Food Delivery Platform
"""

from ai.agents.base import AgentBase, AgentContext
from ai.agents.messaging import AgentMessageBus
from ai.mcp.tools._deterministic import pick, pick_int  # reused, not duplicated - see DEC-0020

_DRIVER_NAMES = ("Alex", "Jordan", "Sam", "Taylor", "Morgan")


class DeliveryAgent(AgentBase):
    name = "delivery_agent"

    def __init__(self, message_bus: AgentMessageBus):
        self._message_bus = message_bus

    async def run(self, context: AgentContext) -> AgentContext:
        order_id = context.data.get("order_id") or context.input
        driver_name = pick(order_id, _DRIVER_NAMES)
        eta_minutes = pick_int(order_id, 10, 45)
        context.data["delivery_agent_result"] = {
            "order_id": order_id, "driver_name": driver_name, "eta_minutes": eta_minutes, "is_mock": True,
        }
        self._message_bus.publish(
            context, self.name, "customer_support_agent", "delivery_dispatched",
            {"order_id": order_id, "driver_name": driver_name, "eta_minutes": eta_minutes},
        )
        return context
