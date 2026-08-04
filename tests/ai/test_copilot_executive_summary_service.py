"""
Tests for ai/copilot/executive_summary_service.py.

ExecutiveSummaryService.build() is a thin composer: it calls
app.routes.dashboard.kpi_bar()/analytics_summary() and formats their
output into a paragraph. Those two functions' own query correctness is
already the responsibility of the dashboard route tests (which run
against the project's real MySQL database - see
docs/governance/DECISION-LOG.md on the accepted MySQL-only baseline for
average-cooking-time, which uses MySQL's TIMESTAMPDIFF and cannot run
against SQLite). This module's tests therefore monkeypatch
dashboard_routes.kpi_bar/analytics_summary with canned, realistic return
values, so ExecutiveSummaryService's OWN composition logic - not
dashboard.py's queries - is what's under test, and these tests run
anywhere (no live database required at all).
"""

from app.routes import dashboard as dashboard_routes
from ai.copilot.executive_summary_service import ExecutiveSummaryService

_KPIS = {
    "total_orders": 12,
    "total_customers": 8,
    "total_revenue": 4599.50,
    "average_order_value": 383.29,
    "pending_orders": 3,
    "preparing_orders": 2,
    "ready_orders": 1,
    "out_for_delivery_orders": 1,
    "delivered_orders": 4,
    "cancelled_orders": 1,
}

_ANALYTICS = {
    "today_revenue": 899.0,
    "orders_per_hour_last_24h": 0.5,
    "top_selling_items": [{"item_name": "Burger", "units_sold": 14}],
    "failed_payments": 1,
    "inventory_alerts_count": 2,
    "average_cooking_time_seconds": 210.5,
}


def test_build_composes_summary_text_from_real_kpi_and_analytics_numbers(monkeypatch):
    monkeypatch.setattr(dashboard_routes, "kpi_bar", lambda db: dict(_KPIS))
    monkeypatch.setattr(dashboard_routes, "analytics_summary", lambda db: dict(_ANALYTICS))

    summary = ExecutiveSummaryService().build(db=None)

    assert "12 total orders" in summary.summary_text
    assert "8 customers" in summary.summary_text
    assert "4,599.50" in summary.summary_text
    assert "3 pending" in summary.summary_text
    assert "Burger (14 units)" in summary.summary_text
    assert "1 order(s) have a failed payment" in summary.summary_text
    assert "2 inventory alert(s) active" in summary.summary_text
    assert summary.kpis == {"kpis": _KPIS, "analytics": _ANALYTICS}


def test_build_omits_optional_warnings_when_nothing_to_flag(monkeypatch):
    clean_analytics = dict(_ANALYTICS)
    clean_analytics["failed_payments"] = 0
    clean_analytics["inventory_alerts_count"] = 0
    monkeypatch.setattr(dashboard_routes, "kpi_bar", lambda db: dict(_KPIS))
    monkeypatch.setattr(dashboard_routes, "analytics_summary", lambda db: clean_analytics)

    summary = ExecutiveSummaryService().build(db=None)

    assert "failed payment" not in summary.summary_text
    assert "inventory alert" not in summary.summary_text


def test_build_omits_top_selling_item_when_none_sold(monkeypatch):
    no_top_seller = dict(_ANALYTICS)
    no_top_seller["top_selling_items"] = []
    monkeypatch.setattr(dashboard_routes, "kpi_bar", lambda db: dict(_KPIS))
    monkeypatch.setattr(dashboard_routes, "analytics_summary", lambda db: no_top_seller)

    summary = ExecutiveSummaryService().build(db=None)

    assert "Top-selling item" not in summary.summary_text
