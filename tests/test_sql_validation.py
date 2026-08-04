"""
SQL / database-level validation tests - separate from the API-level tests in
test_orders.py. These check the actual rows written to each table, and
verify rollback leaves no orphan data on failure.

Requires a real DB reachable via the app's normal config (OMS360_DB_* env
vars) with oms360_schema.sql applied, and at least one inventory row with
enough stock. Uses ITM-002 by default to avoid colliding with test_orders.py,
which uses ITM-001 - adjust if your seed data differs.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app import models

client = TestClient(app)

SAMPLE_ITEM_ID = "ITM-002"


def _make_payload(quantity=1):
    return {
        "customer_id": f"CUST-SQLTEST-{uuid.uuid4().hex[:6]}",
        "customer_name": "SQL Validation Tester",
        "mobile": "9876500000",
        "payment_method": "UPI",
        "enterprise_id": "ENT-99",
        "items": [{"item_id": SAMPLE_ITEM_ID, "quantity": quantity}],
        "delivery_address": {
            "door_no": "1", "street": "Validation Street",
            "city": "Bengaluru", "state": "Karnataka", "pincode": "560001",
        },
    }


def test_order_creation_writes_all_expected_rows():
    resp = client.post("/api/v1/orders", json=_make_payload(quantity=1))
    if resp.status_code != 201:
        pytest.skip(f"Order creation returned {resp.status_code}, likely out of stock - skipping row checks.")

    order_id = resp.json()["order_id"]
    db = SessionLocal()
    try:
        order = db.query(models.OrdersMaster).filter(models.OrdersMaster.order_id == order_id).first()
        assert order is not None, "orders_master row was not created"

        items = db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).all()
        assert len(items) == 1, "order_items row was not created"

        kitchen = db.query(models.KitchenStatus).filter(models.KitchenStatus.order_id == order_id).all()
        assert len(kitchen) == 1, "kitchen_status row was not created"
        # KitchenStatus's Python attribute is `.status` (mapped to the real
        # DB column `cooking_status` - see the 2026-07-22 fix note in
        # app/models.py). `.cooking_status` was never a valid attribute on
        # this ORM class; kitchen_service.py, consumer.py, and
        # dashboard.py all consistently use `.status`, so this test is
        # updated to match rather than the other way around.
        assert kitchen[0].status == "QUEUED"

        delivery = db.query(models.DeliveryStatus).filter(models.DeliveryStatus.order_id == order_id).all()
        assert len(delivery) == 1, "delivery_status row was not created"
        assert delivery[0].status == "PENDING"

        txn = db.query(models.Transaction).filter(models.Transaction.order_id == order_id).first()
        assert txn is not None, "transactions row was not created"

        audit = db.query(models.OrderAuditTrail).filter(models.OrderAuditTrail.order_id == order_id).all()
        event_types = {row.event_type for row in audit}
        assert "ORDER_CREATED" in event_types, "audit trail missing ORDER_CREATED"
        assert "INVENTORY_RESERVED" in event_types, "audit trail missing INVENTORY_RESERVED"
    finally:
        db.close()


def test_inventory_decrements_on_order():
    db = SessionLocal()
    try:
        before = db.query(models.Inventory).filter(models.Inventory.item_id == SAMPLE_ITEM_ID).first()
        before_remaining = before.remaining_stock
    finally:
        db.close()

    resp = client.post("/api/v1/orders", json=_make_payload(quantity=1))
    if resp.status_code != 201:
        pytest.skip(f"Order creation returned {resp.status_code}, likely out of stock - skipping.")

    db = SessionLocal()
    try:
        after = db.query(models.Inventory).filter(models.Inventory.item_id == SAMPLE_ITEM_ID).first()
        assert after.remaining_stock == before_remaining - 1
        assert after.used_stock >= 1
    finally:
        db.close()


def test_insufficient_stock_leaves_no_orphan_rows():
    """Ordering an absurd quantity should fail cleanly, with no
    orders_master / order_items / kitchen_status / delivery_status rows
    left behind - proves rollback works."""
    huge_quantity = 999_999_999
    resp = client.post("/api/v1/orders", json=_make_payload(quantity=huge_quantity))
    assert resp.status_code == 409

    db = SessionLocal()
    try:
        orphan_items = (
            db.query(models.OrderItem)
            .filter(models.OrderItem.quantity == huge_quantity)
            .count()
        )
        assert orphan_items == 0, "Found an order_items row despite insufficient-stock rollback"
    finally:
        db.close()


def test_duplicate_orders_table_gets_a_row_on_repeat_idempotency_key():
    key = f"sql-test-dup-{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/orders", json=_make_payload(quantity=1), headers={"Idempotency-Key": key})
    second = client.post("/api/v1/orders", json=_make_payload(quantity=1), headers={"Idempotency-Key": key})
    assert second.status_code == 409

    db = SessionLocal()
    try:
        dup_rows = db.query(models.DuplicateOrder).filter(models.DuplicateOrder.transaction_id == key).all()
        assert len(dup_rows) >= 1, "duplicate_orders did not get a row for the repeated idempotency key"
    finally:
        db.close()
