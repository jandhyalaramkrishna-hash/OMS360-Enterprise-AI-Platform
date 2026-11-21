"""
Dashboard stock-level consistency tests (2026-11-21).

The Monitoring dashboard's low-stock / out-of-stock lists and counts must be
derived from remaining_stock with the same rule as the low-stock API and the
alert email - not from the stored inventory.status column, which can be
stale (e.g. demo-seeded Salted Fries: stock 12 stored as LOW_STOCK).

Rule (default threshold 5, strictly below):
    0            -> OUT_OF_STOCK
    1..4         -> LOW_STOCK
    5 and above  -> ACTIVE (not listed)
    INACTIVE     -> excluded

Self-contained: in-memory SQLite, no MySQL, no Kafka, no email.
Run:  pytest tests/test_dashboard_stock_levels.py -v
"""

import pathlib
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.routes import dashboard
from app.services import inventory_service

THRESHOLD = 5
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    yield session
    session.close()
    engine.dispose()


def _add(db, item_id, stock, status="ACTIVE", name=None):
    db.add(models.Inventory(item_id=item_id, item_name=name or item_id, price=100,
                            total_stock=max(stock, 0) + 10, remaining_stock=stock,
                            used_stock=10, status=status))
    db.commit()


def _ids(rows):
    return [r["item_id"] for r in rows]


# --------------------------------------------------------------------------
# Boundaries
# --------------------------------------------------------------------------
@pytest.mark.parametrize("stock, expected", [
    (0, "OUT_OF_STOCK"),
    (1, "LOW_STOCK"),
    (2, "LOW_STOCK"),
    (4, "LOW_STOCK"),
    (5, "ACTIVE"),
    (6, "ACTIVE"),
    (12, "ACTIVE"),
    (100, "ACTIVE"),
])
def test_stock_boundaries_on_dashboard(db, stock, expected):
    _add(db, "ITEM-X", stock)
    low = _ids(dashboard._inventory_by_status(db, "LOW_STOCK"))
    out = _ids(dashboard._inventory_by_status(db, "OUT_OF_STOCK"))
    actual = "OUT_OF_STOCK" if out else "LOW_STOCK" if low else "ACTIVE"
    assert actual == expected
    assert dashboard._stock_level_query(db, "LOW_STOCK").count() == (1 if expected == "LOW_STOCK" else 0)
    assert dashboard._stock_level_query(db, "OUT_OF_STOCK").count() == (1 if expected == "OUT_OF_STOCK" else 0)


# --------------------------------------------------------------------------
# Stale stored status must not drive the dashboard
# --------------------------------------------------------------------------
def test_stale_low_stock_status_at_12_is_not_listed(db):
    """Reproduces Finding 1: Salted Fries stock 12 stored as LOW_STOCK."""
    _add(db, "ITEM-FRIES", 12, status="LOW_STOCK", name="Salted Fries")
    assert dashboard._inventory_by_status(db, "LOW_STOCK") == []
    assert dashboard._stock_level_query(db, "LOW_STOCK").count() == 0


def test_stale_active_status_at_2_is_listed_as_low(db):
    """Reproduces production millet idly: stock 2 stored as ACTIVE."""
    _add(db, "ITEM-1002", 2, status="ACTIVE", name="millet idly")
    assert _ids(dashboard._inventory_by_status(db, "LOW_STOCK")) == ["ITEM-1002"]


def test_stale_out_of_stock_status_with_stock_is_not_out(db):
    _add(db, "ITEM-Y", 40, status="OUT_OF_STOCK")
    assert dashboard._inventory_by_status(db, "OUT_OF_STOCK") == []


def test_inactive_items_are_excluded(db):
    _add(db, "ITEM-IN-LOW", 2, status="INACTIVE")
    _add(db, "ITEM-IN-OUT", 0, status="INACTIVE")
    assert dashboard._inventory_by_status(db, "LOW_STOCK") == []
    assert dashboard._inventory_by_status(db, "OUT_OF_STOCK") == []


def test_low_stock_list_is_lowest_first_then_item_id(db):
    _add(db, "ITEM-C", 3)
    _add(db, "ITEM-B", 2)
    _add(db, "ITEM-A", 2)
    _add(db, "ITEM-D", 1)
    assert _ids(dashboard._inventory_by_status(db, "LOW_STOCK")) == ["ITEM-D", "ITEM-A", "ITEM-B", "ITEM-C"]


def test_list_fields_unchanged(db):
    _add(db, "ITEM-A", 3, name="Veg Idly")
    row = dashboard._inventory_by_status(db, "LOW_STOCK")[0]
    assert set(row) == {"item_id", "item_name", "remaining_stock", "total_stock", "price"}
    assert (row["item_name"], row["remaining_stock"]) == ("Veg Idly", 3)


def test_configured_threshold_override_is_respected(db):
    db.add(models.SystemConfiguration(config_key="LOW_STOCK_THRESHOLD", config_value="8"))
    db.commit()
    _add(db, "ITEM-A", 7)
    _add(db, "ITEM-B", 8)
    assert _ids(dashboard._inventory_by_status(db, "LOW_STOCK")) == ["ITEM-A"]


def test_dashboard_does_not_modify_inventory_rows(db):
    _add(db, "ITEM-FRIES", 12, status="LOW_STOCK")
    _add(db, "ITEM-1002", 2, status="ACTIVE")
    dashboard._inventory_by_status(db, "LOW_STOCK")
    dashboard._inventory_by_status(db, "OUT_OF_STOCK")
    dashboard._stock_level_query(db, "LOW_STOCK").count()
    db.expire_all()
    assert db.get(models.Inventory, "ITEM-FRIES").status == "LOW_STOCK"   # read-only: no silent rewrite
    assert db.get(models.Inventory, "ITEM-1002").status == "ACTIVE"


def test_unknown_level_is_rejected(db):
    with pytest.raises(ValueError):
        dashboard._stock_level_query(db, "ACTIVE")


# --------------------------------------------------------------------------
# Consistency with the low-stock API and the alert email list
# --------------------------------------------------------------------------
def _mixed_catalog(db):
    _add(db, "ITEM-SALAD", 0, status="OUT_OF_STOCK", name="Caesar Salad")
    _add(db, "ITEM-1005", 1, status="LOW_STOCK", name="Ghee Idly")
    _add(db, "ITEM-1002", 2, status="ACTIVE", name="millet idly")        # stale
    _add(db, "ITEM-1003", 2, status="LOW_STOCK", name="veg idly")
    _add(db, "ITEM-1004", 3, status="LOW_STOCK", name="Egg masala Dosa")
    _add(db, "ITEM-EDGE", 5, status="ACTIVE", name="Exactly Five")
    _add(db, "ITEM-FRIES", 12, status="LOW_STOCK", name="Salted Fries")  # stale
    _add(db, "ITEM-BURGER", 186, status="ACTIVE", name="Classic Beef Burger")


def test_dashboard_matches_low_stock_api(db):
    _mixed_catalog(db)
    api_ids = [r.item_id for r in inventory_service.get_low_stock(db)]
    dash_ids = _ids(dashboard._inventory_by_status(db, "LOW_STOCK"))
    assert sorted(dash_ids) == sorted(api_ids) == ["ITEM-1002", "ITEM-1003", "ITEM-1004", "ITEM-1005"]


def test_dashboard_matches_out_of_stock_api(db):
    _mixed_catalog(db)
    api_ids = [r.item_id for r in inventory_service.get_out_of_stock(db)]
    assert _ids(dashboard._inventory_by_status(db, "OUT_OF_STOCK")) == api_ids == ["ITEM-SALAD"]


def test_dashboard_matches_alert_email_list(db):
    _mixed_catalog(db)
    email_ids = [t[0] for t in inventory_service._current_low_stock_items(db, THRESHOLD)]
    dash_ids = (_ids(dashboard._inventory_by_status(db, "OUT_OF_STOCK"))
                + _ids(dashboard._inventory_by_status(db, "LOW_STOCK")))
    assert dash_ids == email_ids == ["ITEM-SALAD", "ITEM-1005", "ITEM-1002", "ITEM-1003", "ITEM-1004"]


def test_monitoring_snapshot_inventory_summary_uses_stock_rule(db, monkeypatch):
    """End-to-end through GET /api/v1/dashboard/monitoring's handler, with
    the infrastructure probes (health, Kafka, DLQ) stubbed out."""
    from app.routes import health as health_routes

    ok = {"status": "UP"}
    for name in ("_check_database", "_check_kafka_broker", "_check_disk", "_check_memory",
                 "_check_cpu", "_check_docker", "_check_kafka_producer"):
        monkeypatch.setattr(health_routes, name, lambda *a, **k: dict(ok))
    monkeypatch.setattr(health_routes, "_compute_overall_status", lambda *a, **k: "HEALTHY")
    monkeypatch.setattr(dashboard, "get_dlq_summary",
                        lambda _db: {"total": 0, "most_recent": []})
    monkeypatch.setattr(dashboard, "_check_kafka_consumer", lambda *a, **k: {"status": "UP"})
    monkeypatch.setattr(dashboard, "get_topic_stats", lambda *a, **k: {}, raising=False)

    _mixed_catalog(db)
    result = dashboard.monitoring_snapshot(db=db)

    assert _ids(result["low_stock_items"]) == ["ITEM-1005", "ITEM-1002", "ITEM-1003", "ITEM-1004"]
    assert _ids(result["out_of_stock_items"]) == ["ITEM-SALAD"]
    summary = next(v for v in result.values() if isinstance(v, dict) and "low_stock_count" in v)
    assert (summary["low_stock_count"], summary["out_of_stock_count"]) == (4, 1)


# --------------------------------------------------------------------------
# Seed script and documentation text
# --------------------------------------------------------------------------
def test_demo_seed_fries_is_active_and_has_no_obsolete_alert():
    sql = (REPO_ROOT / "database" / "demo_seed.sql").read_text(encoding="utf-8")
    fries_rows = re.findall(r"\('ITEM-FRIES',\s*'Salted Fries',\s*99\.00,.*?\)", sql)
    assert len(fries_rows) == 2
    assert all("'ACTIVE'" in r and "'LOW_STOCK'" not in r for r in fries_rows)
    # The obsolete demo alert (Fries LOW_STOCK at 12) is removed entirely.
    assert "INSERT INTO inventory_alerts" not in sql
    assert "ops@oms360.demo" not in sql


def test_demo_seed_inventory_statuses_follow_the_rule():
    sql = (REPO_ROOT / "database" / "demo_seed.sql").read_text(encoding="utf-8")
    rows = re.findall(r"\('(ITEM-[A-Z0-9-]+)',\s*'[^']*',\s*[\d.]+,\s*(\d+),\s*(\d+),\s*(\d+),\s*'([A-Z_]+)'\)", sql)
    assert rows, "no inventory rows parsed from demo_seed.sql"
    for item_id, _total, remaining, _used, status in rows:
        remaining = int(remaining)
        expected = "OUT_OF_STOCK" if remaining <= 0 else "LOW_STOCK" if remaining < THRESHOLD else "ACTIVE"
        assert status == expected, f"{item_id}: stock {remaining} seeded as {status}, rule says {expected}"


def test_learning_assistant_describes_default_threshold_of_five():
    text = (REPO_ROOT / "ai" / "copilot" / "learning_assistant_service.py").read_text(encoding="utf-8")
    assert "default of 5" in text
    assert "default of 10" not in text
    assert inventory_service.DEFAULT_LOW_STOCK_THRESHOLD == 5
