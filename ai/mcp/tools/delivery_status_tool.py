"""
AI Service Layer - MCP - Mock Tools - Delivery Status (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

Deterministic mock only - no database, no call into
app/services/delivery_service.py. Given a delivery_id, returns a
plausible, reproducible mock delivery snapshot.
"""

from app.core.logging_config import get_logger

from ai.mcp.base import MCPTool
from ai.mcp.tools._deterministic import pick, pick_int

logger = get_logger("ai.mcp.tools.delivery_status")

_DELIVERY_STATUSES = ("awaiting_pickup", "picked_up", "en_route", "arriving_soon", "delivered")
_DRIVER_NAMES = ("Alex Morgan", "Jordan Lee", "Sam Rivera", "Casey Chen", "Taylor Brooks")


class DeliveryStatusTool(MCPTool):
    name = "delivery_status_lookup"
    description = "Looks up the current status of a delivery by delivery_id. Returns mock data only."
    input_schema = {
        "type": "object",
        "properties": {"delivery_id": {"type": "string", "description": "The delivery identifier to look up."}},
        "required": ["delivery_id"],
    }

    async def execute(self, **kwargs) -> dict:
        delivery_id = kwargs.get("delivery_id")
        if not delivery_id:
            raise ValueError("delivery_id is required by the delivery_status_lookup tool.")

        status = pick(delivery_id, _DELIVERY_STATUSES)
        driver_name = pick(delivery_id, _DRIVER_NAMES)
        eta_minutes = 0 if status == "delivered" else pick_int(delivery_id, 2, 45)

        result = {
            "delivery_id": delivery_id,
            "status": status,
            "driver_name": driver_name,
            "eta_minutes": eta_minutes,
            "is_mock": True,
        }
        logger.info(
            "delivery_status_lookup tool executed",
            extra={"ctx_delivery_id": delivery_id, "ctx_status": status},
        )
        return result
