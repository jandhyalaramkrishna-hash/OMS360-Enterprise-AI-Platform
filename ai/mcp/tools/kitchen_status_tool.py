"""
AI Service Layer - MCP - Mock Tools - Kitchen Status (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

Deterministic mock only - no database, no call into
app/services/kitchen_service.py. Given a kitchen_id, returns a plausible,
reproducible mock kitchen-load snapshot.
"""

from app.core.logging_config import get_logger

from ai.mcp.base import MCPTool
from ai.mcp.tools._deterministic import pick, pick_int

logger = get_logger("ai.mcp.tools.kitchen_status")

_KITCHEN_STATUSES = ("open", "busy", "backlogged", "closed")


class KitchenStatusTool(MCPTool):
    name = "kitchen_status_lookup"
    description = "Looks up the current operational status/load of a restaurant kitchen by kitchen_id. Returns mock data only."
    input_schema = {
        "type": "object",
        "properties": {"kitchen_id": {"type": "string", "description": "The kitchen/restaurant identifier to look up."}},
        "required": ["kitchen_id"],
    }

    async def execute(self, **kwargs) -> dict:
        kitchen_id = kwargs.get("kitchen_id")
        if not kitchen_id:
            raise ValueError("kitchen_id is required by the kitchen_status_lookup tool.")

        status = pick(kitchen_id, _KITCHEN_STATUSES)
        active_orders = 0 if status == "closed" else pick_int(kitchen_id, 0, 25)
        avg_prep_time_minutes = pick_int(kitchen_id, 8, 35)

        result = {
            "kitchen_id": kitchen_id,
            "status": status,
            "active_orders": active_orders,
            "avg_prep_time_minutes": avg_prep_time_minutes,
            "is_mock": True,
        }
        logger.info(
            "kitchen_status_lookup tool executed",
            extra={"ctx_kitchen_id": kitchen_id, "ctx_status": status},
        )
        return result
