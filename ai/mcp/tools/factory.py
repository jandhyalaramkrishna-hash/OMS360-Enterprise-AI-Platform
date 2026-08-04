"""
AI Service Layer - MCP - Mock Tool Factory (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

MCPToolFactory owns construction of the four Sprint 6 mock tools, mirroring
ai.providers.factory.ProviderFactory's role for the provider framework
(Sprint 4): one place that knows the full set of known tool classes, so
ai/dependencies.py doesn't hardcode a tool list inline and a future real
tool implementation has one obvious place to be added.
"""

from ai.mcp.tools.delivery_status_tool import DeliveryStatusTool
from ai.mcp.tools.inventory_lookup_tool import InventoryLookupTool
from ai.mcp.tools.kitchen_status_tool import KitchenStatusTool
from ai.mcp.tools.order_lookup_tool import OrderLookupTool

_TOOL_CLASSES = (OrderLookupTool, InventoryLookupTool, DeliveryStatusTool, KitchenStatusTool)


class MCPToolFactory:
    @staticmethod
    def known_tool_names() -> list:
        return sorted(cls.name for cls in _TOOL_CLASSES)

    @staticmethod
    def create_all() -> list:
        """Returns one freshly-constructed instance of every known Sprint
        6 mock tool. Every tool here is stateless (no constructor
        arguments needed), so a fresh instance per call is cheap and
        avoids any accidental shared mutable state between callers."""
        return [cls() for cls in _TOOL_CLASSES]
