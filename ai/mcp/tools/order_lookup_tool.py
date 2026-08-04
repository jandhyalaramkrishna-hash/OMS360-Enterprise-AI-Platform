"""
AI Service Layer - MCP - Mock Tools - Order Lookup (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

Deterministic mock only - no database, no Kafka, no call into
app/services/order_service.py. Given an order_id, returns a plausible,
reproducible mock order snapshot.
"""

from app.core.logging_config import get_logger

from ai.mcp.base import MCPTool
from ai.mcp.tools._deterministic import pick, pick_int

logger = get_logger("ai.mcp.tools.order_lookup")

_ORDER_STATUSES = ("placed", "confirmed", "preparing", "ready_for_pickup", "out_for_delivery", "delivered")
_MENU_ITEMS = ("Margherita Pizza", "Chicken Biryani", "Veggie Burger", "Butter Chicken", "Caesar Salad", "Pad Thai")


class OrderLookupTool(MCPTool):
    name = "order_lookup"
    description = "Looks up the status and contents of a customer order by order_id. Returns mock data only."
    input_schema = {
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "The order identifier to look up."}},
        "required": ["order_id"],
    }

    async def execute(self, **kwargs) -> dict:
        order_id = kwargs.get("order_id")
        if not order_id:
            raise ValueError("order_id is required by the order_lookup tool.")

        status = pick(order_id, _ORDER_STATUSES)
        item_count = pick_int(order_id, 1, 4)
        items = [pick(f"{order_id}:{i}", _MENU_ITEMS) for i in range(item_count)]
        total_amount = round(pick_int(order_id, 899, 4999) / 100, 2)

        result = {
            "order_id": order_id,
            "status": status,
            "items": items,
            "total_amount": total_amount,
            "currency": "USD",
            "is_mock": True,
        }
        logger.info("order_lookup tool executed", extra={"ctx_order_id": order_id, "ctx_status": status})
        return result
