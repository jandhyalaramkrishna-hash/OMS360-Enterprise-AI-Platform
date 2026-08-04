"""
AI Copilot - Executive Summary Service
OMS-360 Enterprise Food Delivery Platform

Reuses app.routes.dashboard's existing kpi_bar() and analytics_summary()
functions directly (calling them as plain Python functions with an
explicit db= argument, bypassing their FastAPI Depends(get_db) default)
rather than duplicating their query logic - "reuse existing APIs
wherever possible," applied literally. Composes their real numbers into
a short paragraph via a fixed template. Never LLM-generated (no real
numbers pass through a provider) - matches the same "business facts
always come from real data" rule ai.copilot.business_qa_service applies,
since an executive summary is still a business-facts surface, not a
reasoning task.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.routes import dashboard as dashboard_routes


@dataclass(frozen=True)
class ExecutiveSummary:
    summary_text: str
    kpis: dict


class ExecutiveSummaryService:
    """Construct via ai.dependencies.get_executive_summary_service(), not
    directly. Stateless - holds no collaborators, since it only calls
    the existing dashboard route functions with an explicit db session."""

    def build(self, db: Session) -> ExecutiveSummary:
        kpis = dashboard_routes.kpi_bar(db=db)
        analytics = dashboard_routes.analytics_summary(db=db)

        parts = [
            f"You have {kpis['total_orders']} total orders from {kpis['total_customers']} customers, "
            f"generating ₹{kpis['total_revenue']:,.2f} in revenue (average order value ₹{kpis['average_order_value']:,.2f}).",
            f"Right now: {kpis['pending_orders']} pending, {kpis['preparing_orders']} preparing, "
            f"{kpis['ready_orders']} ready, {kpis['out_for_delivery_orders']} out for delivery, "
            f"{kpis['delivered_orders']} delivered, {kpis['cancelled_orders']} cancelled.",
            f"Today so far: ₹{analytics['today_revenue']:,.2f} in revenue, "
            f"{analytics['orders_per_hour_last_24h']} orders/hour over the last 24h.",
        ]
        if analytics["top_selling_items"]:
            top = analytics["top_selling_items"][0]
            parts.append(f"Top-selling item: {top['item_name']} ({top['units_sold']} units).")
        if analytics["failed_payments"] > 0:
            parts.append(f"⚠ {analytics['failed_payments']} order(s) have a failed payment - worth a look.")
        if analytics["inventory_alerts_count"] > 0:
            parts.append(f"⚠ {analytics['inventory_alerts_count']} inventory alert(s) active.")

        return ExecutiveSummary(summary_text=" ".join(parts), kpis={"kpis": kpis, "analytics": analytics})
