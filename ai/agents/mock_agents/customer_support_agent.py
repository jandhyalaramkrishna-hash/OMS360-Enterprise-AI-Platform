"""
AI Service Layer - Agents - Mock Agents - Customer Support Agent (Sprint 7)
OMS-360 Enterprise Food Delivery Platform
"""

from ai.agents.base import AgentBase, AgentContext
from ai.agents.messaging import AgentMessageBus


class CustomerSupportAgent(AgentBase):
    name = "customer_support_agent"

    def __init__(self, message_bus: AgentMessageBus):
        self._message_bus = message_bus

    async def run(self, context: AgentContext) -> AgentContext:
        order_id = context.data.get("order_id") or context.input
        inbound = self._message_bus.messages_for(context, self.name)
        latest_update = inbound[-1].content if inbound else "no_updates_yet"
        context.data["customer_support_agent_result"] = {
            "order_id": order_id,
            "latest_update": latest_update,
            "messages_received": len(inbound),
            "is_mock": True,
        }
        return context
