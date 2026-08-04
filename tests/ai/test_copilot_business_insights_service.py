"""
Tests for ai/copilot/business_insights_service.py — each rule-based
threshold, against a real (SQLite, in-memory) database. No mocking: every
row is a real app.models row, and BusinessInsightsService.build() runs
its actual SQLAlchemy queries.
"""

import datetime as dt

from app import models
from app.core.enums import InventoryStatus, KitchenStatus, OrderStatus, PaymentStatus
from ai.copilot.business_insights_service import BusinessInsightsService


def _mk_order(order_id, order_status=OrderStatus.RECEIVED.value, payment_status=PaymentStatus.PAID.value):
    return models.OrdersMaster(
        order_id=order_id, transaction_id=f"TXN-{order_id}", customer_name="Cust", customer_id=f"C-{order_id}",
        mobile="9000000000", grand_total=100.0, total_amount=100.0,
        payment_status=payment_status, order_status=order_status, created_at=dt.datetime.utcnow(),
    )


def test_no_orders_yields_single_info_insight(copilot_db):
    insights = BusinessInsightsService().build(copilot_db)
    assert len(insights) == 1
    assert insights[0].severity == "info"
    assert "No orders" in insights[0].message


def test_healthy_state_yields_single_no_issues_insight(copilot_db):
    copilot_db.add(_mk_order("ORD-1"))
    copilot_db.commit()
    insights = BusinessInsightsService().build(copilot_db)
    assert len(insights) == 1
    assert insights[0].severity == "info"
    assert "healthy" in insights[0].message.lower()


def test_high_cancellation_rate_triggers_warning(copilot_db):
    copilot_db.add_all([
        _mk_order("ORD-1", order_status=OrderStatus.CANCELLED.value),
        _mk_order("ORD-2", order_status=OrderStatus.RECEIVED.value),
    ])
    copilot_db.commit()
    insights = BusinessInsightsService().build(copilot_db)
    messages = [i for i in insights if "Cancellation rate" in i.message]
    assert len(messages) == 1
    assert messages[0].severity == "warning"
    assert "50.0%" in messages[0].message


def test_failed_payment_triggers_warning(copilot_db):
    copilot_db.add(_mk_order("ORD-1", payment_status=PaymentStatus.FAILED.value))
    copilot_db.commit()
    insights = BusinessInsightsService().build(copilot_db)
    messages = [i for i in insights if "failed payment" in i.message]
    assert len(messages) == 1
    assert messages[0].severity == "warning"


def test_out_of_stock_triggers_critical(copilot_db):
    copilot_db.add(_mk_order("ORD-1"))
    copilot_db.add(models.Inventory(
        item_id="ITEM-1", item_name="Fries", price=99.0, total_stock=10,
        remaining_stock=0, used_stock=10, status=InventoryStatus.OUT_OF_STOCK.value,
    ))
    copilot_db.commit()
    insights = BusinessInsightsService().build(copilot_db)
    messages = [i for i in insights if "out of stock" in i.message]
    assert len(messages) == 1
    assert messages[0].severity == "critical"


def test_low_stock_triggers_warning(copilot_db):
    copilot_db.add(_mk_order("ORD-1"))
    copilot_db.add(models.Inventory(
        item_id="ITEM-1", item_name="Burger", price=199.0, total_stock=10,
        remaining_stock=2, used_stock=8, status=InventoryStatus.LOW_STOCK.value,
    ))
    copilot_db.commit()
    insights = BusinessInsightsService().build(copilot_db)
    messages = [i for i in insights if "running low" in i.message]
    assert len(messages) == 1
    assert messages[0].severity == "warning"


def test_pending_backlog_triggers_info(copilot_db):
    copilot_db.add_all([_mk_order(f"ORD-{i}", order_status=OrderStatus.RECEIVED.value) for i in range(10)])
    copilot_db.commit()
    insights = BusinessInsightsService().build(copilot_db)
    messages = [i for i in insights if "backlog is building" in i.message]
    assert len(messages) == 1
    assert messages[0].severity == "info"
    assert "10 orders" in messages[0].message


def test_kitchen_backlog_triggers_warning_when_cooking_exceeds_expected_time(copilot_db, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SIM_COOKING_SECONDS", 60)
    order = _mk_order("ORD-1")
    copilot_db.add(order)
    copilot_db.commit()
    stuck_start = dt.datetime.utcnow() - dt.timedelta(seconds=600)
    copilot_db.add(models.KitchenStatus(
        order_id="ORD-1", transaction_id="TXN-ORD-1", item_id="ITEM-1", item_assignment="Burger",
        quantity=1, station_id="ST-1", status=KitchenStatus.COOKING.value, chef_name="Chef A",
        started_at=stuck_start,
    ))
    copilot_db.commit()
    insights = BusinessInsightsService().build(copilot_db)
    messages = [i for i in insights if "stuck" in i.message]
    assert len(messages) == 1
    assert messages[0].severity == "warning"
