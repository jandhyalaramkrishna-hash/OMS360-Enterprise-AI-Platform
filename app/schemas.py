"""
OMS-360 Enterprise Order Management System - Version 1.0
Pydantic request/response schemas, with input validation and OpenAPI
examples (so Swagger shows real request/response bodies, not just field
names).

Design decision (documented, since the old schemas.py did it differently):
`transaction_id` is SERVER-generated, not client-supplied - see
app/services/order_service.py. The old schemas.py asked the client for one,
which only works if the client can guarantee global uniqueness.

Validation added in this round:
  - mobile: must be exactly 10 digits (India-style, matching the seed data's
    format - adjust the regex if you need international numbers).
  - pincode: must be exactly 6 digits.
  - quantity: must be a positive integer (already had gt=0; unchanged).
  - customer_name / city / state / street / door_no: must not be blank.
Pydantic raises a 422 automatically for any of these; the message is
formatted consistently by app/core/exceptions.py's validation handler.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator

MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")   # 10 digits, Indian mobile convention
PINCODE_REGEX = re.compile(r"^\d{6}$")


class AddressPayload(BaseModel):
    door_no: str = Field(..., min_length=1, examples=["12/B"])
    street: str = Field(..., min_length=1, examples=["M G Road"])
    city: str = Field(..., min_length=1, examples=["Bengaluru"])
    state: str = Field(..., min_length=1, examples=["Karnataka"])
    pincode: str = Field(..., examples=["560001"])

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v):
        if not PINCODE_REGEX.match(v):
            raise ValueError("pincode must be exactly 6 digits")
        return v


class OrderItemPayload(BaseModel):
    # Example matches an item actually seeded by database/demo_seed.sql
    # (the script docker-compose.yml mounts as 04_demo_seed.sql) so
    # Swagger's "Try it out" pre-filled body works against a fresh DB
    # out of the box. Do not reintroduce "ITM-xxx" IDs here - that scheme
    # belongs to enterprise_demo_seed.sql, which is not wired into any
    # environment (see docs/governance/DECISION-LOG.md).
    item_id: str = Field(..., examples=["ITEM-BURGER"])
    quantity: int = Field(gt=0, examples=[2])


class OrderCreatePayload(BaseModel):
    customer_id: Optional[str] = Field(default=None, examples=["CUST-001"])
    customer_name: str = Field(..., min_length=1, examples=["Anil Kumar"])
    mobile: str = Field(..., examples=["9876543210"])
    payment_method: str = Field(default="UPI", examples=["UPI"])
    enterprise_id: Optional[str] = Field(default=None, examples=["ENT-99"])
    items: List[OrderItemPayload] = Field(..., min_length=1)
    delivery_address: AddressPayload

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v):
        if not MOBILE_REGEX.match(v):
            raise ValueError("mobile must be a 10-digit number starting with 6-9")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "customer_id": "CUST-001",
                "customer_name": "Anil Kumar",
                "mobile": "9876543210",
                "payment_method": "UPI",
                "enterprise_id": "ENT-99",
                "items": [{"item_id": "ITEM-BURGER", "quantity": 2}],
                "delivery_address": {
                    "door_no": "12/B", "street": "M G Road",
                    "city": "Bengaluru", "state": "Karnataka", "pincode": "560001",
                },
            }]
        }
    }


class OrderItemResponse(BaseModel):
    item_id: str
    item_name: str
    quantity: int
    price: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    order_id: str
    transaction_id: str
    customer_name: str
    grand_total: float
    payment_status: str
    order_status: str
    fraud_status: str
    created_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "order_id": "ORD-A1B2C3D4E5",
                "transaction_id": "TXN-F6G7H8I9J0K1",
                "customer_name": "Anil Kumar",
                "grand_total": 260.0,
                "payment_status": "PENDING",
                "order_status": "RECEIVED",
                "fraud_status": "CLEAR",
                "created_at": "2026-07-15T10:30:00",
                "items": [{"item_id": "ITEM-BURGER", "item_name": "Classic Beef Burger", "quantity": 2, "price": 249.0}],
            }
        }


class InventoryResponse(BaseModel):
    item_id: str
    item_name: str
    price: float
    total_stock: int
    remaining_stock: int
    used_stock: int
    status: str
    category: Optional[str] = None
    unit: Optional[str] = None

    class Config:
        from_attributes = True


class RestockRequest(BaseModel):
    quantity: int = Field(gt=0, examples=[100])
    reason: Optional[str] = Field(default="Manual restock", examples=["Weekly supplier delivery"])


VALID_INVENTORY_STATUSES = {"ACTIVE", "LOW_STOCK", "OUT_OF_STOCK", "INACTIVE"}


class InventoryUpdateRequest(BaseModel):
    """Backs PUT /api/v1/inventory/{item_id} - the Inventory Dashboard's
    "Update Inventory" dialog. `stock` (added alongside price/status) is
    an ADMIN CORRECTION of remaining_stock (e.g. a physical stock count
    doesn't match the system) - it is intentionally separate from the
    order-reservation path (reserve_stock()) and the supplier-restock path
    (POST /restock); every stock change here is still ledgered
    (movement_type=ADJUSTMENT) so it stays fully auditable.

    2026-07-27 addition (see docs/governance/DECISION-LOG.md): `category`
    and `unit` were added alongside the pre-existing `item_name` so the
    Update Inventory dialog can edit Item Name, Category, and Unit -
    Product Owner request. Both are plain optional string fields backed by
    new nullable `items.category`/`items.unit` and
    `inventory.category`/`inventory.unit` columns
    (migrations/004_add_item_category_unit.sql) - nullable so every
    existing row is unaffected until an admin fills them in."""
    price: Optional[float] = Field(default=None, gt=0, examples=[249.0])
    status: Optional[str] = Field(default=None, examples=["ACTIVE"])
    item_name: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0, examples=[150],
                                  description="New remaining_stock value (admin correction, not a delta).")
    category: Optional[str] = Field(default=None, examples=["Beverages"])
    unit: Optional[str] = Field(default=None, examples=["plate"])

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_INVENTORY_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_INVENTORY_STATUSES)}")
        return v


class InventoryCreateRequest(BaseModel):
    """Backs POST /api/v1/inventory - the Inventory Dashboard's "Add New
    Item" dialog. item_id is intentionally NOT accepted here - the server
    always generates it (see inventory_service._generate_item_id), per
    explicit Product Owner instruction ("The system should generate the
    Item Number automatically"). category/unit are deliberately NOT part
    of this dialog (out of scope for the 2026-07-27 request, which asked
    only for Update Inventory to gain them) - a newly created item's
    category/unit are simply NULL until edited via Update Inventory."""
    item_name: str = Field(..., min_length=1, examples=["Paneer Tikka Wrap"])
    price: float = Field(..., gt=0, examples=[189.0])
    total_stock: int = Field(..., ge=0, examples=[100])
    status: Optional[str] = Field(default=None, examples=["ACTIVE"])

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_INVENTORY_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_INVENTORY_STATUSES)}")
        return v


class InventoryLedgerResponse(BaseModel):
    ledger_id: int
    item_id: str
    movement_type: str
    quantity_change: int
    remaining_stock_after: int
    reference_order_id: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryAlertResponse(BaseModel):
    alert_id: int
    item_id: str
    item_name: str
    remaining_stock: int
    threshold_value: int
    alert_type: str
    notification_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEventResponse(BaseModel):
    audit_id: int
    order_id: str
    transaction_id: str
    event_type: str
    event_details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SystemHealthResponse(BaseModel):
    status: str
    dependencies: Dict[str, str]

    class Config:
        json_schema_extra = {
            "example": {
                "status": "HEALTHY",
                "dependencies": {
                    "database": "UP", "kafka": "UP", "application": "UP",
                    "disk": "OK (42% used)", "memory": "OK (61% used)",
                },
            }
        }


class DashboardOperationsResponse(BaseModel):
    total_orders: int
    kitchen_queue: int
    delivery_queue: int
    revenue: float
    duplicate_count: int
    failed_count: int


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str
