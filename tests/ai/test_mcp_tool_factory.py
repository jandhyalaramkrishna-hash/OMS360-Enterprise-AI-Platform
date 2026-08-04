"""
Tests for ai/mcp/tools/factory.py — MCPToolFactory owns construction of
the four known Sprint 6 mock tools.
"""

from ai.mcp.base import MCPTool
from ai.mcp.tools.delivery_status_tool import DeliveryStatusTool
from ai.mcp.tools.factory import MCPToolFactory
from ai.mcp.tools.inventory_lookup_tool import InventoryLookupTool
from ai.mcp.tools.kitchen_status_tool import KitchenStatusTool
from ai.mcp.tools.order_lookup_tool import OrderLookupTool


def test_known_tool_names_lists_all_four_sorted():
    assert MCPToolFactory.known_tool_names() == sorted(
        ["order_lookup", "inventory_lookup", "delivery_status_lookup", "kitchen_status_lookup"]
    )


def test_create_all_returns_four_mcp_tool_instances():
    tools = MCPToolFactory.create_all()
    assert len(tools) == 4
    assert all(isinstance(tool, MCPTool) for tool in tools)


def test_create_all_returns_one_instance_of_each_known_class():
    tools = MCPToolFactory.create_all()
    classes = {type(tool) for tool in tools}
    assert classes == {OrderLookupTool, InventoryLookupTool, DeliveryStatusTool, KitchenStatusTool}


def test_create_all_returns_fresh_instances_each_call():
    first = MCPToolFactory.create_all()
    second = MCPToolFactory.create_all()
    assert all(a is not b for a, b in zip(first, second))
