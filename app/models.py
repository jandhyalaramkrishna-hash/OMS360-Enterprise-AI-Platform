"""
OMS-360 Enterprise Order Management System - Version 1.0
SQLAlchemy ORM models.

Every column below is copied from `oms360_schema.sql` (the master schema you
designated) - table names, column names, types, nullability and defaults all
match it exactly. Nothing here invents a column that doesn't exist in the
live database, and nothing silently drops a column that does.

Known intentional differences vs. the earlier draft models.py you uploaded:
  - OrdersMaster.transaction_id is now a REAL mapped Column (unique, not
    nullable), not a hardcoded string constant. The old file set it to the
    literal string "SIMULATED_TX_ID", which meant it was never actually
    written to the database.
  - OrderItem.item_name is now mapped (it's NOT NULL with no default on
    the live table - omitting it, as the old models.py did, would have
    caused every insert to fail).

2026-07-22 audit fix (see docs/governance/DECISION-LOG.md): four columns in
this file did not match the live oms360_schema.sql and were breaking the
app outright:
  - Item.created_at used an undefined `DateTime` type (NameError on import
    - this alone crashed the entire application at startup, since app.main
    imports app.routes.orders -> app.services.order_service -> app.models)
    and was renamed to a non-existent "order_date" column. Fixed to match
    the real `created_at TIMESTAMP` column (same as Inventory).
  - OrdersMaster.grand_total was mapped to a non-existent "order_total"
    column. The real column is `grand_total` - fixed to map directly.
  - OrdersMaster.created_at was renamed to a non-existent "order_date"
    column. The real column is `created_at` - fixed to map directly.
  - KitchenStatus.status was mapped to a non-existent "status" column.
    The real column (per oms360_schema.sql and demo_seed.sql) is
    `cooking_status` - fixed to map to it. The Python attribute name
    (`.status`) is unchanged, so no call site elsewhere needed to change.

2026-07-27 addition (see docs/governance/DECISION-LOG.md): Item.category/
Item.unit and Inventory.category/Inventory.unit were added, backed by new
nullable columns from migrations/004_add_item_category_unit.sql (NOT part
of the original oms360_schema.sql - flagged here the same way
OrderAuditTrail/InventoryLedger below are flagged as migration-only
tables). Nullable, no default, so every pre-existing row is unaffected.
"""

from sqlalchemy import (
    Column, String, Integer, Numeric, Text, ForeignKey, TIMESTAMP
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Item(Base):
    """`items` table - menu/catalog registry. Structurally identical to
    `inventory`; both exist in the live DB (see understanding doc, Section 6)."""
    __tablename__ = "items"

    item_id = Column(String(50), primary_key=True)
    item_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    total_stock = Column(Integer, nullable=False, default=1000)
    remaining_stock = Column(Integer, nullable=False, default=1000)
    used_stock = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Inventory(Base):
    """`inventory` table - the table actually used for live stock checks
    during order placement."""
    __tablename__ = "inventory"

    item_id = Column(String(50), primary_key=True)
    item_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    total_stock = Column(Integer, nullable=False, default=1000)
    remaining_stock = Column(Integer, nullable=False, default=1000)
    used_stock = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class OrdersMaster(Base):
    __tablename__ = "orders_master"

    order_id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), nullable=False, unique=True)
    customer_name = Column(String(255), nullable=False)
    customer_id = Column(String(50), nullable=True)
    mobile = Column(String(20), nullable=False)
    mobile_number = Column(String(20), nullable=True)
    grand_total = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=True)
    payment_method = Column(String(50), nullable=True, default="ONLINE")
    payment_status = Column(String(50), nullable=False, default="PENDING")
    fraud_status = Column(String(50), nullable=False, default="CLEAR")
    order_status = Column(String(50), nullable=False, default="RECEIVED")
    live_window_track = Column(String(100), nullable=False, default="SUCCESS_FLOW")
    enterprise_id = Column(String(50), nullable=True)
    door_no = Column(String(50), nullable=True)
    street = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    kitchen_rows = relationship("KitchenStatus", back_populates="order", cascade="all, delete-orphan")
    delivery_rows = relationship("DeliveryStatus", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders_master.order_id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(50), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(10, 2), nullable=False)

    order = relationship("OrdersMaster", back_populates="items")


class KitchenStatus(Base):
    __tablename__ = "kitchen_status"

    kitchen_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders_master.order_id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(String(50), nullable=False)
    item_id = Column(String(50), nullable=False)
    item_assignment = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    station_id = Column(String(50), nullable=False)
    status = Column("cooking_status", String(50), nullable=False, default="COOKING")
    chef_name = Column(String(100), nullable=False)
    started_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    order = relationship("OrdersMaster", back_populates="kitchen_rows")


class DeliveryStatus(Base):
    __tablename__ = "delivery_status"

    delivery_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders_master.order_id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(String(50), nullable=False)
    item_id = Column(String(50), nullable=False)
    transit_payload = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    delivery_person = Column(String(100), nullable=True)

    order = relationship("OrdersMaster", back_populates="delivery_rows")


class FailedOrder(Base):
    __tablename__ = "failed_orders"

    order_id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    failed_at = Column(TIMESTAMP, server_default=func.now())


class DuplicateOrder(Base):
    __tablename__ = "duplicate_orders"

    order_id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), nullable=False)
    detected_at = Column(TIMESTAMP, server_default=func.now())


class DlqOrder(Base):
    __tablename__ = "dlq_orders"

    order_id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), nullable=False)
    payload = Column(Text, nullable=True)
    moved_at = Column(TIMESTAMP, server_default=func.now())


class InventoryAlert(Base):
    __tablename__ = "inventory_alerts"

    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(20), nullable=False)
    item_name = Column(String(100), nullable=False)
    remaining_stock = Column(Integer, nullable=False)
    threshold_value = Column(Integer, nullable=False)
    alert_type = Column(String(30), default="LOW_STOCK")
    notification_type = Column(String(20), default="EMAIL")
    notification_status = Column(String(20), default="PENDING")
    recipient_email = Column(String(150), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class SystemConfiguration(Base):
    __tablename__ = "system_configuration"

    config_key = Column(String(100), primary_key=True)
    config_value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(50), primary_key=True)
    order_id = Column(String(50), nullable=False)
    payment_method = Column(String(30), nullable=True)
    payment_status = Column(String(30), nullable=True)
    transaction_amount = Column(Numeric(10, 2), nullable=True)
    transaction_time = Column(TIMESTAMP, server_default=func.now())


class OrderAuditTrail(Base):
    """`order_audit_trail` - NOT part of oms360_schema.sql (the master
    schema). Added via migrations/002_add_audit_trail.sql, at your explicit
    request for an audit trail feature. Records every state transition an
    order goes through, independent of the structured logs (see
    app/core/logging_config.py) - this table is what the
    GET /api/v1/orders/{order_id}/audit endpoint reads from."""
    __tablename__ = "order_audit_trail"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders_master.order_id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_details = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class InventoryLedger(Base):
    """`inventory_ledger` - NOT part of oms360_schema.sql. Added via
    migrations/003_add_inventory_ledger.sql, V1.1 Requirement #5
    ("Inventory Movement / Stock Ledger"). One row per stock change
    (restock, reserve, release, adjustment) - this is what backs
    GET /api/v1/inventory/history and the consumption/usage reporting."""
    __tablename__ = "inventory_ledger"

    ledger_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), nullable=False)
    movement_type = Column(String(20), nullable=False)   # RESTOCK|RESERVE|RELEASE|ADJUSTMENT
    quantity_change = Column(Integer, nullable=False)     # positive for restock, negative for reserve
    remaining_stock_after = Column(Integer, nullable=False)
    reference_order_id = Column(String(50), nullable=True)
    reason = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
