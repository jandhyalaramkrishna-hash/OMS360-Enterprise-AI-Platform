"""
AI Service Layer - Agents - Mock Agents - Kitchen Agent (Sprint 7)
OMS-360 Enterprise Food Delivery Platform
"""

from ai.agents.base import AgentBase, AgentContext
from ai.agents.messaging import AgentMessageBus
from ai.mcp.tools._deterministic import pick_int  # reused, not duplicated - see DEC-0020


class KitchenAgent(AgentBase):
    name = "kitchen_agent"

    def __init__(self, message_bus: AgentMessageBus):
        self._message_bus = message_bus

    async def run(self, context: AgentContext) -> AgentContext:
        order_id = context.data.get("order_id") or context.input
        prep_minutes = pick_int(order_id, 5, 30)
        context.data["kitchen_agent_result"] = {
            "order_id": order_id, "prep_time_minutes": prep_minutes, "is_mock": True,
        }
        self._message_bus.publish(
            context, self.name, "delivery_agent", "order_ready_for_pickup",
            {"order_id": order_id, "prep_time_minutes": prep_minutes},
        )
        return context
