"""
AI Service Layer - MCP - Mock Tools - Inventory Lookup (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

Deterministic mock only - no database, no call into
app/services/inventory_service.py. Given an item_id, returns a plausible,
reproducible mock stock snapshot.
"""

from app.core.logging_config import get_logger

from ai.mcp.base import MCPTool
from ai.mcp.tools._deterministic import pick_int

logger = get_logger("ai.mcp.tools.inventory_lookup")

_REORDER_THRESHOLD = 20


class InventoryLookupTool(MCPTool):
    name = "inventory_lookup"
    description = "Looks up current mock stock levels for a menu/inventory item by item_id. Returns mock data only."
    input_schema = {
        "type": "object",
        "properties": {"item_id": {"type": "string", "description": "The inventory item identifier to look up."}},
        "required": ["item_id"],
    }

    async def execute(self, **kwargs) -> dict:
        item_id = kwargs.get("item_id")
        if not item_id:
            raise ValueError("item_id is required by the inventory_lookup tool.")

        quantity = pick_int(item_id, 0, 150)
        in_stock = quantity > 0

        result = {
            "item_id": item_id,
            "in_stock": in_stock,
            "quantity": quantity,
            "reorder_threshold": _REORDER_THRESHOLD,
            "needs_reorder": quantity <= _REORDER_THRESHOLD,
            "is_mock": True,
        }
        logger.info("inventory_lookup tool executed", extra={"ctx_item_id": item_id, "ctx_quantity": quantity})
        return result
