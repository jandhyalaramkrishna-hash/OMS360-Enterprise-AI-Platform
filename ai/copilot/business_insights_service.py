"""
AI Copilot - Business Insights Service
OMS-360 Enterprise Food Delivery Platform

A handful of rule-based observations over real, live data - not an LLM
summary. Each rule reads directly from the same tables
app/routes/dashboard.py already reads, applying a simple, explainable
threshold (documented inline) rather than a black-box judgment call.
Kept as its own module (not folded into ExecutiveSummaryService) since
insights are conditional/flagged observations, not a fixed-shape KPI
readout - a future phase could add more rules here without touching the
summary template.
"""

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.core.enums import InventoryStatus, KitchenStatus, OrderStatus, PaymentStatus


@dataclass(frozen=True)
class Insight:
    severity: str  # "info" | "warning" | "critical"
    message: str


class BusinessInsightsService:
    """Construct via ai.dependencies.get_business_insights_service(), not
    directly. Stateless."""

    def build(self, db: Session) -> list:
        insights = []

        total_orders = db.query(func.count(models.OrdersMaster.order_id)).scalar() or 0
        if total_orders == 0:
            return [Insight("info", "No orders have been placed yet - insights will appear once there is order activity.")]

        cancelled = (
            db.query(func.count(models.OrdersMaster.order_id))
            .filter(models.OrdersMaster.order_status == OrderStatus.CANCELLED.value)
            .scalar()
            or 0
        )
        cancellation_rate = (cancelled / total_orders) * 100 if total_orders else 0.0
        if cancellation_rate >= 10:
            insights.append(Insight(
                "warning",
                f"Cancellation rate is {cancellation_rate:.1f}% ({cancelled} of {total_orders} orders) - above the 10% watch threshold.",
            ))

        failed_payments = (
            db.query(func.count(models.OrdersMaster.order_id))
            .filter(models.OrdersMaster.payment_status == PaymentStatus.FAILED.value)
            .scalar()
            or 0
        )
        if failed_payments > 0:
            insights.append(Insight("warning", f"{failed_payments} order(s) currently have a failed payment status."))

        out_of_stock = (
            db.query(func.count(models.Inventory.item_id))
            .filter(models.Inventory.status == InventoryStatus.OUT_OF_STOCK.value)
            .scalar()
            or 0
        )
        if out_of_stock > 0:
            insights.append(Insight("critical", f"{out_of_stock} menu item(s) are completely out of stock - customers ordering these will be blocked."))

        low_stock = (
            db.query(func.count(models.Inventory.item_id))
            .filter(models.Inventory.status == InventoryStatus.LOW_STOCK.value)
            .scalar()
            or 0
        )
        if low_stock > 0:
            insights.append(Insight("warning", f"{low_stock} menu item(s) are running low on stock - consider restocking soon."))

        # Kitchen backlog: items still COOKING that have exceeded the
        # simulated cooking time (settings.SIM_COOKING_SECONDS) - the same
        # real deadline app/routes/dashboard.py's kitchen-ops ETA already
        # uses, not an invented threshold.
        stuck_cutoff = func.now()
        cooking_rows = (
            db.query(models.KitchenStatus.started_at)
            .filter(models.KitchenStatus.status == KitchenStatus.COOKING.value)
            .all()
        )
        import datetime as _dt

        now = _dt.datetime.utcnow()
        overdue = sum(
            1
            for (started_at,) in cooking_rows
            if started_at and (now - started_at).total_seconds() > settings.SIM_COOKING_SECONDS
        )
        if overdue > 0:
            insights.append(Insight(
                "warning",
                f"{overdue} kitchen item(s) have exceeded the expected {settings.SIM_COOKING_SECONDS}s cooking time and may be stuck.",
            ))

        pending = (
            db.query(func.count(models.OrdersMaster.order_id))
            .filter(models.OrdersMaster.order_status == OrderStatus.RECEIVED.value)
            .scalar()
            or 0
        )
        if pending >= 10:
            insights.append(Insight("info", f"{pending} orders are pending kitchen pickup - backlog is building."))

        if not insights:
            insights.append(Insight("info", "No issues detected - orders, inventory, kitchen, and payments all look healthy."))

        return insights
