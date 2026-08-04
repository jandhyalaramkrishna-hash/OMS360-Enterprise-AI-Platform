"""
AI Service Layer - Agents - Mock Agents - Order Agent (Sprint 7)
OMS-360 Enterprise Food Delivery Platform
"""

from ai.agents.base import AgentBase, AgentContext
from ai.agents.messaging import AgentMessageBus
from ai.mcp.tools._deterministic import pick  # reused, not duplicated - see DEC-0020

_ORDER_STATUSES = ("received", "confirmed", "preparing", "ready", "out_for_delivery", "delivered")


class OrderAgent(AgentBase):
    name = "order_agent"

    def __init__(self, message_bus: AgentMessageBus):
        self._message_bus = message_bus

    async def run(self, context: AgentContext) -> AgentContext:
        order_id = context.data.get("order_id") or context.input
        status = pick(order_id, _ORDER_STATUSES)
        context.data["order_agent_result"] = {"order_id": order_id, "status": status, "is_mock": True}
        self._message_bus.publish(
            context, self.name, "kitchen_agent", "order_received_for_prep",
            {"order_id": order_id, "status": status},
        )
        return context
