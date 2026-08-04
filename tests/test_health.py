"""
Basic smoke tests. Requires the DB (from oms360_schema.sql) to be reachable
at whatever OMS360_DB_HOST/etc. point to - these are integration tests, not
pure unit tests, consistent with this being a QA-validation-focused project.

Run with: pytest tests/
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "UP"


def test_version():
    resp = client.get("/version")
    assert resp.status_code == 200
    assert "version" in resp.json()


def test_health_reports_database_dependency():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "dependencies" in body
    assert "database" in body["dependencies"]


def test_inventory_list_shape():
    resp = client.get("/api/v1/inventory")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        for field in ["item_id", "item_name", "price", "remaining_stock", "status"]:
            assert field in row
