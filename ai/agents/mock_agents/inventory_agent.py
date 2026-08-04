"""
AI Service Layer - Agents - Mock Agents - Inventory Agent (Sprint 7)
OMS-360 Enterprise Food Delivery Platform
"""

from ai.agents.base import AgentBase, AgentContext
from ai.agents.messaging import AgentMessageBus
from ai.mcp.tools._deterministic import pick_int  # reused, not duplicated - see DEC-0020


class InventoryAgent(AgentBase):
    name = "inventory_agent"

    def __init__(self, message_bus: AgentMessageBus):
        self._message_bus = message_bus

    async def run(self, context: AgentContext) -> AgentContext:
        order_id = context.data.get("order_id") or context.input
        quantity = pick_int(order_id, 0, 100)
        in_stock = quantity > 0
        context.data["inventory_agent_result"] = {
            "order_id": order_id, "in_stock": in_stock, "quantity": quantity, "is_mock": True,
        }
        self._message_bus.publish(
            context, self.name, "order_agent", "stock_check_complete",
            {"order_id": order_id, "in_stock": in_stock, "quantity": quantity},
        )
        return context
