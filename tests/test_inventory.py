"""
Inventory Dashboard "Update Inventory" / "Add New Item" integration
tests. Same convention as test_orders.py: imports the real app.main.app
and hits it via TestClient - runs against whatever DATABASE_URL is
actually configured (the live MySQL container, not a mock), so these
verify the real, deployed behavior. Every test creates its own item via
POST /api/v1/inventory first (auto-generated Item Number) rather than
depending on demo_seed.sql rows, so repeated runs never collide with
each other or with real order traffic reserving stock concurrently.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_item(item_name="QA Test Item", price=99.0, total_stock=50, status=None):
    payload = {"item_name": item_name, "price": price, "total_stock": total_stock}
    if status:
        payload["status"] = status
    resp = client.post("/api/v1/inventory", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_add_new_item_generates_item_number_and_appears_in_list():
    created = _create_item()
    assert created["item_id"].startswith("ITEM-")
    assert created["remaining_stock"] == 50
    assert created["status"] == "ACTIVE"

    all_items = client.get("/api/v1/inventory").json()
    assert any(i["item_id"] == created["item_id"] for i in all_items)


def test_add_new_item_writes_initial_restock_ledger_entry():
    created = _create_item(total_stock=75)
    history = client.get("/api/v1/inventory/history", params={"item_id": created["item_id"]}).json()
    assert history, "expected at least one ledger row for a newly created item"
    assert history[0]["movement_type"] == "RESTOCK"
    assert history[0]["quantity_change"] == 75


def test_update_inventory_price_and_status_only():
    created = _create_item()
    resp = client.put(f"/api/v1/inventory/{created['item_id']}", json={"price": 149.0, "status": "INACTIVE"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["price"] == 149.0
    assert body["status"] == "INACTIVE"
    assert body["remaining_stock"] == created["remaining_stock"]  # stock untouched


def test_update_inventory_stock_correction_writes_adjustment_ledger_and_recomputes_status():
    created = _create_item(total_stock=50)
    resp = client.put(f"/api/v1/inventory/{created['item_id']}", json={"stock": 3})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["remaining_stock"] == 3
    assert body["status"] == "LOW_STOCK"

    history = client.get("/api/v1/inventory/history", params={"item_id": created["item_id"]}).json()
    assert history[0]["movement_type"] == "ADJUSTMENT"
    assert history[0]["quantity_change"] == 3 - 50

    alerts = [a for a in client.get("/api/v1/inventory/alerts").json() if a["item_id"] == created["item_id"]]
    assert any(a["alert_type"] == "LOW_STOCK" for a in alerts)


def test_update_inventory_stock_recovers_status_to_active():
    created = _create_item(total_stock=5, status="LOW_STOCK")
    resp = client.put(f"/api/v1/inventory/{created['item_id']}", json={"stock": 500})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"


def test_update_inventory_unknown_item_returns_404():
    resp = client.put("/api/v1/inventory/ITEM-DOES-NOT-EXIST-XYZ", json={"price": 10})
    assert resp.status_code == 404


def test_update_inventory_invalid_status_returns_422():
    created = _create_item()
    resp = client.put(f"/api/v1/inventory/{created['item_id']}", json={"status": "NOT_A_REAL_STATUS"})
    assert resp.status_code == 422
    # DEC-<TBD>: exc.errors() ctx.error must be sanitized to a string, or
    # this 422 crashes into a 500 (see app/core/exceptions.py).
    assert "fields" in resp.json()


def test_add_new_item_invalid_price_returns_422():
    resp = client.post("/api/v1/inventory", json={"item_name": "Bad Item", "price": -5, "total_stock": 10})
    assert resp.status_code == 422
