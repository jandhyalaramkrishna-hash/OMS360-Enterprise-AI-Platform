"""
AI Service Layer - Agents - Mock Agents - Analytics Agent (Sprint 7)
OMS-360 Enterprise Food Delivery Platform
"""

from ai.agents.base import AgentBase, AgentContext
from ai.agents.messaging import AgentMessageBus


class AnalyticsAgent(AgentBase):
    """Terminal agent in a typical run sequence: summarizes what happened
    across the other agents' contributions (context.history) and the mock
    messages they exchanged (context.messages). Publishes nothing further
    - it observes, it does not participate in the lifecycle itself."""

    name = "analytics_agent"

    def __init__(self, message_bus: AgentMessageBus):
        self._message_bus = message_bus

    async def run(self, context: AgentContext) -> AgentContext:
        context.data["analytics_agent_result"] = {
            "agents_run": len(context.history),
            "messages_exchanged": len(context.messages),
            "is_mock": True,
        }
        return context
