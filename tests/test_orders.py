"""
Order creation integration tests. Uses whatever item_id already exists in
`inventory` per database/demo_seed.sql (the seed script docker-compose.yml
actually mounts as 04_demo_seed.sql - e.g. ITEM-BURGER) - adjust
SAMPLE_ITEM_ID below if your seed data uses different IDs.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_ITEM_ID = "ITEM-BURGER"

VALID_ORDER_PAYLOAD = {
    "customer_id": "CUST-TEST-001",
    "customer_name": "QA Test Customer",
    "mobile": "9999999999",
    "payment_method": "UPI",
    "enterprise_id": "ENT-99",
    "items": [{"item_id": SAMPLE_ITEM_ID, "quantity": 1}],
    "delivery_address": {
        "door_no": "1",
        "street": "Test Street",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
    },
}


def test_create_order_success_or_known_stock_error():
    resp = client.post("/api/v1/orders", json=VALID_ORDER_PAYLOAD)
    # Accept either success, or a 409 if the seeded stock has run out from
    # repeated test runs - both are "correctly handled" outcomes, a 500
    # would not be.
    assert resp.status_code in (201, 409)


def test_create_order_unknown_item_returns_400():
    payload = dict(VALID_ORDER_PAYLOAD)
    payload["items"] = [{"item_id": "ITM-DOES-NOT-EXIST", "quantity": 1}]
    resp = client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 400


def test_create_order_idempotency_key_blocks_duplicate():
    key = "test-idempotency-key-001"
    first = client.post(
        "/api/v1/orders", json=VALID_ORDER_PAYLOAD, headers={"Idempotency-Key": key}
    )
    second = client.post(
        "/api/v1/orders", json=VALID_ORDER_PAYLOAD, headers={"Idempotency-Key": key}
    )
    # First may succeed or hit stock limits; second with the same key must
    # always be rejected as a duplicate while the TTL window is open.
    assert second.status_code == 409
