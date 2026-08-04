"""
AI Service Layer - Agents - Agent Factory (Sprint 7)
OMS-360 Enterprise Food Delivery Platform

Mirrors ai/mcp/tools/factory.py's MCPToolFactory: owns construction of
every known mock agent, injecting the shared AgentMessageBus into each
one. known_agent_names()/create_all() let callers (ai/dependencies.py,
tests) discover and build the full agent set without hardcoding the
class list anywhere else.
"""

from ai.agents.mock_agents.analytics_agent import AnalyticsAgent
from ai.agents.mock_agents.customer_support_agent import CustomerSupportAgent
from ai.agents.mock_agents.delivery_agent import DeliveryAgent
from ai.agents.mock_agents.inventory_agent import InventoryAgent
from ai.agents.mock_agents.kitchen_agent import KitchenAgent
from ai.agents.mock_agents.order_agent import OrderAgent
from ai.agents.messaging import AgentMessageBus

_AGENT_CLASSES = (
    OrderAgent,
    InventoryAgent,
    KitchenAgent,
    DeliveryAgent,
    CustomerSupportAgent,
    AnalyticsAgent,
)


class AgentFactory:
    def __init__(self, message_bus: AgentMessageBus):
        self._message_bus = message_bus

    def known_agent_names(self) -> list:
        return sorted(cls.name for cls in _AGENT_CLASSES)

    def create_all(self) -> list:
        return [cls(self._message_bus) for cls in _AGENT_CLASSES]
