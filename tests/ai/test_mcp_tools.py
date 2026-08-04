"""
Tests for ai/mcp/tools/ — the four Sprint 6 mock tools. Each must be
deterministic (same id -> same output, every call), vary across different
ids, return only mock data (an `is_mock: True` marker, no real
lookup), and raise a clear error when its required id argument is
missing.
"""

import asyncio

import pytest

from ai.mcp.tools.delivery_status_tool import DeliveryStatusTool
from ai.mcp.tools.inventory_lookup_tool import InventoryLookupTool
from ai.mcp.tools.kitchen_status_tool import KitchenStatusTool
from ai.mcp.tools.order_lookup_tool import OrderLookupTool


def test_order_lookup_is_deterministic_and_shaped_correctly():
    tool = OrderLookupTool()
    first = asyncio.run(tool.execute(order_id="ORD-1"))
    second = asyncio.run(tool.execute(order_id="ORD-1"))
    assert first == second
    assert first["order_id"] == "ORD-1"
    assert first["status"] in (
        "placed", "confirmed", "preparing", "ready_for_pickup", "out_for_delivery", "delivered",
    )
    assert isinstance(first["items"], list) and len(first["items"]) >= 1
    assert first["total_amount"] > 0
    assert first["is_mock"] is True


def test_order_lookup_varies_across_different_ids():
    tool = OrderLookupTool()
    results = {asyncio.run(tool.execute(order_id=f"ORD-{i}"))["status"] for i in range(20)}
    assert len(results) > 1


def test_order_lookup_requires_order_id():
    tool = OrderLookupTool()
    with pytest.raises(ValueError):
        asyncio.run(tool.execute())
    with pytest.raises(ValueError):
        asyncio.run(tool.execute(order_id=""))


def test_inventory_lookup_is_deterministic_and_shaped_correctly():
    tool = InventoryLookupTool()
    first = asyncio.run(tool.execute(item_id="ITEM-1"))
    second = asyncio.run(tool.execute(item_id="ITEM-1"))
    assert first == second
    assert first["item_id"] == "ITEM-1"
    assert isinstance(first["quantity"], int) and first["quantity"] >= 0
    assert first["in_stock"] == (first["quantity"] > 0)
    assert first["needs_reorder"] == (first["quantity"] <= first["reorder_threshold"])
    assert first["is_mock"] is True


def test_inventory_lookup_requires_item_id():
    tool = InventoryLookupTool()
    with pytest.raises(ValueError):
        asyncio.run(tool.execute())


def test_delivery_status_is_deterministic_and_shaped_correctly():
    tool = DeliveryStatusTool()
    first = asyncio.run(tool.execute(delivery_id="DEL-1"))
    second = asyncio.run(tool.execute(delivery_id="DEL-1"))
    assert first == second
    assert first["delivery_id"] == "DEL-1"
    assert first["status"] in ("awaiting_pickup", "picked_up", "en_route", "arriving_soon", "delivered")
    assert first["driver_name"]
    assert first["is_mock"] is True


def test_delivery_status_delivered_has_zero_eta():
    tool = DeliveryStatusTool()
    delivered_id = next(
        f"DEL-{i}" for i in range(200)
        if asyncio.run(tool.execute(delivery_id=f"DEL-{i}"))["status"] == "delivered"
    )
    result = asyncio.run(tool.execute(delivery_id=delivered_id))
    assert result["eta_minutes"] == 0


def test_delivery_status_requires_delivery_id():
    tool = DeliveryStatusTool()
    with pytest.raises(ValueError):
        asyncio.run(tool.execute())


def test_kitchen_status_is_deterministic_and_shaped_correctly():
    tool = KitchenStatusTool()
    first = asyncio.run(tool.execute(kitchen_id="KTC-1"))
    second = asyncio.run(tool.execute(kitchen_id="KTC-1"))
    assert first == second
    assert first["kitchen_id"] == "KTC-1"
    assert first["status"] in ("open", "busy", "backlogged", "closed")
    assert isinstance(first["active_orders"], int)
    assert isinstance(first["avg_prep_time_minutes"], int)
    assert first["is_mock"] is True


def test_kitchen_status_closed_has_zero_active_orders():
    tool = KitchenStatusTool()
    closed_id = next(
        f"KTC-{i}" for i in range(200)
        if asyncio.run(tool.execute(kitchen_id=f"KTC-{i}"))["status"] == "closed"
    )
    result = asyncio.run(tool.execute(kitchen_id=closed_id))
    assert result["active_orders"] == 0


def test_kitchen_status_requires_kitchen_id():
    tool = KitchenStatusTool()
    with pytest.raises(ValueError):
        asyncio.run(tool.execute())
