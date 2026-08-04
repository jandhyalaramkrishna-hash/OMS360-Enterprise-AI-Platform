"""
OMS-360 Enterprise Order Management System - Version 1.1
Enums replacing every magic string in the codebase (Requirement #4).

IMPORTANT: these enums' VALUES match the existing string values already
stored in the database exactly (e.g. OrderStatus.RECEIVED.value ==
"RECEIVED"). This is what makes this a safe, additive refactor - existing
rows and existing API contracts are unaffected, because
`str(SomeEnum.MEMBER)` via `.value` serializes identically to the old raw
string. SQLAlchemy columns still store VARCHAR; enums are used at the
Python layer only, converted at the boundary.
"""

from enum import Enum


class OrderStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class KitchenStatus(str, Enum):
    QUEUED = "QUEUED"
    COOKING = "COOKING"
    READY = "READY"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"


class FraudStatus(str, Enum):
    CLEAR = "CLEAR"
    SUSPECTED = "SUSPECTED"
    BLOCKED = "BLOCKED"


class InventoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INACTIVE = "INACTIVE"


class AuditEventType(str, Enum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_VALIDATED = "ORDER_VALIDATED"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    KITCHEN_ASSIGNED = "KITCHEN_ASSIGNED"
    KITCHEN_STARTED = "KITCHEN_STARTED"
    KITCHEN_COMPLETED = "KITCHEN_COMPLETED"
    DELIVERY_ASSIGNED = "DELIVERY_ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"
    DUPLICATE_REJECTED = "DUPLICATE_REJECTED"


class KafkaTopics(str, Enum):
    ORDER_CREATED = "order.created"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    KITCHEN_ACCEPTED = "kitchen.accepted"
    KITCHEN_REJECTED = "kitchen.rejected"
    DELIVERY_ASSIGNED = "delivery.assigned"
    DELIVERY_COMPLETED = "delivery.completed"
    INVENTORY_UPDATED = "inventory.updated"
    NOTIFICATION_SENT = "notification.sent"
    ORDER_DLQ = "order.dlq"
    ORDER_RETRY = "order.retry"


class InventoryMovementType(str, Enum):
    """Used by inventory_ledger (migrations/003) - not a DB enum, a Python-side
    classification of each stock movement row."""
    RESTOCK = "RESTOCK"
    RESERVE = "RESERVE"
    RELEASE = "RELEASE"
    ADJUSTMENT = "ADJUSTMENT"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
