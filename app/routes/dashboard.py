"""
Dashboard aggregate endpoints. GET /operations is unchanged from V1
(Requirement #11: "current operational dashboard endpoints should remain
intact"). GET /analytics is new (V1.1).

Everything below /operations and /analytics (live-orders, kitchen-ops,
delivery-ops, alerts, kpis, monitoring) was added to power the two
Enterprise Dashboard HTML pages (app/static/operations_dashboard.html and
app/static/monitoring_dashboard.html). All of it reads real rows from the
same tables the rest of the API already uses - no new tables, no static/
fabricated business data. A few fields are clearly-labeled derived
estimates because the master schema (oms360_schema.sql) has no columns
for them:
  - delivery OTP code: delivery_status has no otp column at all. The code
    shown is deterministically derived from the real order_id (same order
    always yields the same code), not random and not stored - it exists
    only so the dashboard can visualize the "OTP verified on delivery"
    step the business asked for. otp_generated/otp_verified themselves ARE
    real, computed straight from the real `status` column.
  - live GPS position: delivery_status has no lat/lng/timestamp columns.
    The dashboard animates a rider icon along a fixed illustrative route
    client-side, driven by the real delivery status - this is the "Live
    GPS Simulation" the business explicitly asked for, not a claim of real
    telemetry.
  - kitchen ETA (kitchen-ops): kitchen_status.started_at IS a real column.
    eta_at/eta_seconds are computed as started_at + settings.SIM_COOKING_SECONDS
    (the same constant app/messaging/consumer.py actually sleeps on), so
    this is a real deadline the consumer will actually hit, not a guess.
    Null once the row is READY.
  - delivery "Assigned At" / ETA (delivery-ops): delivery_status has no
    timestamp columns at all (see average_delivery_time_note below), so
    there is no assigned_at column to read. app/messaging/consumer.py's
    own orchestration calls delivery_service.dispatch() immediately after
    kitchen_service.complete_cooking() for the same order/item - so the
    matching kitchen_status row's updated_at (the real moment it flipped
    to READY) is used as the assigned_at estimate, and eta_at is that
    plus settings.SIM_DELIVERY_SECONDS. Both are null until the delivery
    row leaves PENDING, and eta_at is null again once DELIVERED.
"""

import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.config import settings
from app.core.enums import KitchenStatus, DeliveryStatus, OrderStatus, PaymentStatus
from app.core.kafka_admin import get_topic_stats, get_dlq_summary
from app.core import metrics as metrics_module
from app.database import get_db, get_pool_stats
from app.services import kitchen_service, delivery_service, inventory_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

# --- Business-rule validation (Priority: "invalid state combos on the
# dashboard") -----------------------------------------------------------
# Defines which order_status values are legitimate for a given
# payment_status, per the required OMS-360 workflow:
#   PAID    -> RECEIVED -> PREPARING -> READY -> OUT_FOR_DELIVERY -> DELIVERED
#   FAILED  -> FAILED or CANCELLED only
#   PENDING -> RECEIVED only (payment not yet confirmed)
#   REFUNDED-> DELIVERED or CANCELLED only
# This does NOT hide or drop rows with an unexpected combination - hiding
# rows from an ops dashboard can bury a real production bug. Instead each
# row is annotated with `state_valid` (bool) and, when false, `state_issue`
# (a short human-readable reason), so the row still shows up but is
# clearly flagged instead of presented as if it were a normal state.
_VALID_ORDER_STATUS_BY_PAYMENT = {
    PaymentStatus.PENDING.value: {OrderStatus.RECEIVED.value},
    PaymentStatus.PAID.value: {
        OrderStatus.RECEIVED.value, OrderStatus.PREPARING.value, OrderStatus.READY.value,
        OrderStatus.OUT_FOR_DELIVERY.value, OrderStatus.DELIVERED.value,
    },
    PaymentStatus.FAILED.value: {OrderStatus.FAILED.value, OrderStatus.CANCELLED.value},
    PaymentStatus.REFUNDED.value: {OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value},
}


def _check_state_validity(payment_status: str, order_status: str) -> tuple[bool, str | None]:
    allowed = _VALID_ORDER_STATUS_BY_PAYMENT.get(payment_status)
    if allowed is None:
        return False, f"Unrecognized payment_status '{payment_status}'"
    if order_status not in allowed:
        return False, f"payment_status={payment_status} cannot have order_status={order_status}"
    return True, None


@router.get("/operations", response_model=schemas.DashboardOperationsResponse,
            summary="Operational snapshot (unchanged from V1)")
def operations_summary(db: Session = Depends(get_db)):
    total_orders = db.query(func.count(models.OrdersMaster.order_id)).scalar() or 0
    kitchen_queue = (
        db.query(func.count(models.KitchenStatus.kitchen_id))
       .filter(models.KitchenStatus.status.in_([KitchenStatus.QUEUED.value, KitchenStatus.COOKING.value]))
        .scalar() or 0
    )
    delivery_queue = (
        db.query(func.count(models.DeliveryStatus.delivery_id))
        .filter(models.DeliveryStatus.status.in_([DeliveryStatus.PENDING.value, DeliveryStatus.OUT_FOR_DELIVERY.value]))
        .scalar() or 0
    )
    revenue = db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0)).scalar() or 0.0
    duplicate_count = db.query(func.count(models.DuplicateOrder.order_id)).scalar() or 0
    failed_count = db.query(func.count(models.FailedOrder.order_id)).scalar() or 0

    return schemas.DashboardOperationsResponse(
        total_orders=total_orders, kitchen_queue=kitchen_queue, delivery_queue=delivery_queue,
        revenue=float(revenue), duplicate_count=duplicate_count, failed_count=failed_count,
    )


@router.get("/analytics", summary="Analytics dashboard (V1.1)",
            description="Today's/monthly revenue, top-selling items, average order value, "
                        "orders-per-hour, kitchen/delivery load, pending orders, failed payments, "
                        "inventory alert count.")
def analytics_summary(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    today_revenue = (
        db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0))
        .filter(models.OrdersMaster.created_at >= today_start)
        .scalar() or 0.0
    )
    monthly_revenue = (
        db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0))
        .filter(models.OrdersMaster.created_at >= month_start)
        .scalar() or 0.0
    )

    top_items = (
        db.query(models.OrderItem.item_name, func.sum(models.OrderItem.quantity).label("units"))
        .group_by(models.OrderItem.item_name)
        .order_by(func.sum(models.OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    total_orders = db.query(func.count(models.OrdersMaster.order_id)).scalar() or 0
    total_revenue = db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0)).scalar() or 0.0
    avg_order_value = float(total_revenue) / total_orders if total_orders else 0.0

    pending_orders = (
        db.query(func.count(models.OrdersMaster.order_id))
        .filter(models.OrdersMaster.order_status == "RECEIVED")
        .scalar() or 0
    )
    failed_payments = (
        db.query(func.count(models.OrdersMaster.order_id))
        .filter(models.OrdersMaster.payment_status == PaymentStatus.FAILED.value)
        .scalar() or 0
    )

    kitchen_load = (
        db.query(func.count(models.KitchenStatus.kitchen_id))
        .filter(models.KitchenStatus.status == KitchenStatus.COOKING.value)
        .scalar() or 0
    )
    delivery_load = (
        db.query(func.count(models.DeliveryStatus.delivery_id))
        .filter(models.DeliveryStatus.status == DeliveryStatus.OUT_FOR_DELIVERY.value)
        .scalar() or 0
    )

    orders_last_24h = (
        db.query(func.count(models.OrdersMaster.order_id))
        .filter(models.OrdersMaster.created_at >= now - timedelta(hours=24))
        .scalar() or 0
    )
    orders_per_hour = round(orders_last_24h / 24.0, 2)

    inventory_alerts_count = db.query(func.count(models.InventoryAlert.alert_id)).scalar() or 0

    return {
        "today_revenue": float(today_revenue),
        "monthly_revenue": float(monthly_revenue),
        "top_selling_items": [{"item_name": name, "units_sold": int(units)} for name, units in top_items],
        "average_order_value": round(avg_order_value, 2),
        "average_cooking_time_seconds": round(kitchen_service.get_average_cooking_time_seconds(db), 2),
        "average_delivery_time_seconds": delivery_service.get_average_delivery_time_seconds(db),
        "average_delivery_time_note": "unavailable - delivery_status has no timestamp columns in the master schema",
        "pending_orders": pending_orders,
        "failed_payments": failed_payments,
        "orders_per_hour_last_24h": orders_per_hour,
        "kitchen_load": kitchen_load,
        "delivery_load": delivery_load,
        "inventory_alerts_count": inventory_alerts_count,
    }


# ---------------------------------------------------------------------------
# V1.1 Enterprise Dashboard endpoints (Operations Center + Monitoring Center)
# ---------------------------------------------------------------------------

def _otp_for_order(order_id: str) -> str:
    """Deterministic 4-digit display code derived from the real order_id.
    Not stored anywhere, not random - same order always shows the same
    code. See module docstring for why this exists."""
    digest = hashlib.sha256(order_id.encode()).hexdigest()
    return str(int(digest[:8], 16) % 10000).zfill(4)


# ---------------------------------------------------------------------------
# Monitoring Center UX redesign (2026-07-25) - severity taxonomy, sample-data
# tagging, and an extended alert feed. Scoped to GET /monitoring only: the
# existing GET /alerts feed powering the Operations Center dashboard (and its
# HIGH/MEDIUM/LOW severities) is untouched, so that page's behavior does not
# change.
# ---------------------------------------------------------------------------

# Four-level severity, per the Product Owner's explicit ordering.
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFORMATION": 3}


def _is_sample_record(record_id: str | None) -> bool:
    """True for rows inserted by database/demo_seed.sql - every seeded
    order/transaction id it writes is prefixed DEMO- (e.g. DEMO-ORD-001,
    DEMO-TXN-001; see database/demo_seed.sql). Used to tag sample/demo rows
    structurally instead of relying on free text buried in a reason field."""
    return bool(record_id) and record_id.upper().startswith("DEMO-")


def _check_kafka_consumer(kafka_check: dict, counters: dict) -> dict:
    """Best-effort consumer liveness signal, derived only from data this
    process already has - NOT a real probe of the oms360-consumer
    container/process (that would require the Docker socket mounted into
    this container, the same tradeoff app/routes/health.py::_check_docker()
    already declined for the same reason). UP means real evidence the
    consumer has processed at least one event since this engine process
    started; IDLE means the broker is reachable but no such evidence exists
    yet (not proof of failure); DOWN means the broker itself is unreachable,
    so the consumer cannot possibly be working. Clearly-labeled derived
    status, matching the pattern this file already uses for OTP/ETA fields
    (see module docstring)."""
    if not settings.KAFKA_ENABLED:
        return {"status": "DISABLED", "note": "Kafka is disabled in this environment."}
    if not kafka_check.get("broker_reachable"):
        return {"status": "DOWN", "note": "Kafka broker unreachable - the consumer cannot be running."}
    consumed = counters.get("kafka_consume_success_total", 0)
    if consumed > 0:
        return {"status": "UP", "note": f"{consumed} event(s) consumed since this engine process started."}
    return {"status": "IDLE", "note": "Broker reachable, but no events consumed yet by this engine process - "
                                       "consumer liveness not yet confirmed."}


def _kitchen_delays(db: Session, limit: int = 20) -> list[dict]:
    """Kitchen rows still QUEUED/COOKING whose real ETA (started_at +
    settings.SIM_COOKING_SECONDS, the same deadline app/messaging/consumer.py
    itself sleeps on - see kitchen_ops() above) has already passed."""
    now = datetime.utcnow()
    rows = (
        db.query(models.KitchenStatus, models.OrdersMaster.customer_name)
        .join(models.OrdersMaster, models.KitchenStatus.order_id == models.OrdersMaster.order_id)
        .filter(models.KitchenStatus.status.in_([KitchenStatus.QUEUED.value, KitchenStatus.COOKING.value]))
        .order_by(models.KitchenStatus.started_at.asc())
        .limit(limit)
        .all()
    )
    out = []
    for k, customer_name in rows:
        started = k.started_at or now
        eta_at = started + timedelta(seconds=settings.SIM_COOKING_SECONDS)
        if eta_at >= now:
            continue
        out.append({
            "order_id": k.order_id,
            "customer": customer_name,
            "chef": k.chef_name,
            "item": k.item_assignment,
            "started_at": k.started_at.isoformat() if k.started_at else None,
            "eta_at": eta_at.isoformat(),
            "overdue_seconds": int((now - eta_at).total_seconds()),
            "is_sample": _is_sample_record(k.order_id),
        })
    return out


def _payment_failures(db: Session, limit: int = 20) -> dict:
    """Orders where payment_status=FAILED - a normal, valid business outcome
    (see _VALID_ORDER_STATUS_BY_PAYMENT above), distinct from the
    failed_orders table (system/creation-time errors, see
    order_service._record_failed_order - only called from create_order's
    generic exception handler, never for a declined payment)."""
    q = db.query(models.OrdersMaster).filter(models.OrdersMaster.payment_status == PaymentStatus.FAILED.value)
    total = q.count()
    recent = q.order_by(models.OrdersMaster.created_at.desc()).limit(limit).all()
    return {
        "total": total,
        "recent": [
            {
                "order_id": o.order_id, "customer_name": o.customer_name,
                "transaction_id": o.transaction_id, "amount": float(o.grand_total),
                "failed_at": o.created_at.isoformat() if o.created_at else None,
                "is_sample": _is_sample_record(o.order_id),
            }
            for o in recent
        ],
    }


def _stock_level_query(db: Session, status: str):
    """2026-11-21 (dashboard consistency fix): LOW_STOCK / OUT_OF_STOCK are
    derived from remaining_stock with the same threshold the low-stock API
    and alert email use (inventory_service._get_low_stock_threshold, default
    5) - not from the stored inventory.status column, which can be stale
    (e.g. demo-seeded rows or items created before the rule changed).
        remaining_stock <= 0              -> OUT_OF_STOCK
        0 < remaining_stock < threshold   -> LOW_STOCK
        remaining_stock >= threshold      -> ACTIVE (not listed)
    INACTIVE items are excluded, matching the alert email list. Read-only."""
    threshold = inventory_service._get_low_stock_threshold(db)
    query = db.query(models.Inventory).filter(
        or_(models.Inventory.status.is_(None), models.Inventory.status != "INACTIVE"))
    if status == "OUT_OF_STOCK":
        return query.filter(models.Inventory.remaining_stock <= 0)
    if status == "LOW_STOCK":
        return query.filter(models.Inventory.remaining_stock > 0,
                            models.Inventory.remaining_stock < threshold)
    raise ValueError(f"unsupported stock level: {status}")


def _inventory_by_status(db: Session, status: str, limit: int = 20) -> list[dict]:
    rows = (
        _stock_level_query(db, status)
        .order_by(models.Inventory.remaining_stock.asc(), models.Inventory.item_id.asc())
        .limit(limit)
        .all()
    )
    return [
        {"item_id": i.item_id, "item_name": i.item_name, "remaining_stock": i.remaining_stock,
         "total_stock": i.total_stock, "price": float(i.price)}
        for i in rows
    ]


def _monitoring_alerts(db: Session, dlq_recent: list, failed_recent: list, duplicate_recent: list,
                        payment_failed_recent: list, kitchen_delay_rows: list, limit: int = 50) -> list[dict]:
    """The full Monitoring Center alert universe: everything GET /alerts
    already covers (inventory low/out-of-stock, failed orders, duplicate
    orders) PLUS DLQ events, payment failures, and kitchen delays - each
    tagged with one of the four Monitoring Center severities and an
    `is_active` flag (true when the underlying condition still holds right
    now, e.g. an item that is still LOW_STOCK; false for point-in-time
    events like a past order failure). Independent of GET /alerts /
    business_alerts() above, which keeps its original 3-level severity for
    the Operations Center dashboard."""
    alerts = []

    for a in db.query(models.InventoryAlert).order_by(models.InventoryAlert.created_at.desc()).limit(limit).all():
        is_out = (a.alert_type or "") == "OUT_OF_STOCK"
        alerts.append({
            "type": "OUT_OF_STOCK" if is_out else "LOW_STOCK",
            "severity": "HIGH" if is_out else "MEDIUM",
            "message": f"{a.item_name} ({a.item_id}): {a.remaining_stock} left, threshold {a.threshold_value}",
            "occurred_at": a.created_at.isoformat() if a.created_at else None,
            "is_active": True,
            "is_sample": False,
        })

    for f in failed_recent:
        alerts.append({
            "type": "ORDER_FAILED", "severity": "CRITICAL",
            "message": f"Order {f['order_id']} failed: {(f.get('reason') or 'unknown reason')[:120]}",
            "occurred_at": f["failed_at"], "is_active": False, "is_sample": f.get("is_sample", False),
        })

    for d in duplicate_recent:
        alerts.append({
            "type": "DUPLICATE_ORDER", "severity": "INFORMATION",
            "message": f"Duplicate request rejected (marker {d['order_id']})",
            "occurred_at": d["detected_at"], "is_active": False, "is_sample": d.get("is_sample", False),
        })

    for dq in dlq_recent:
        alerts.append({
            "type": "DLQ_EVENT", "severity": "CRITICAL",
            "message": f"Order {dq['order_id']} moved to the Dead Letter Queue after exhausting retries",
            "occurred_at": dq["moved_at"], "is_active": True, "is_sample": dq.get("is_sample", False),
        })

    for p in payment_failed_recent:
        alerts.append({
            "type": "PAYMENT_FAILURE", "severity": "HIGH",
            "message": f"Payment failed for order {p['order_id']} ({p['customer_name']})",
            "occurred_at": p["failed_at"], "is_active": True, "is_sample": p.get("is_sample", False),
        })

    for k in kitchen_delay_rows:
        alerts.append({
            "type": "KITCHEN_DELAY", "severity": "MEDIUM",
            "message": f"Order {k['order_id']} ({k['item']}) is {k['overdue_seconds']}s past its cooking ETA",
            "occurred_at": k["started_at"], "is_active": True, "is_sample": k.get("is_sample", False),
        })

    # Two stable sorts achieve "severity first (Critical..Information), newest
    # first within the same severity": sort by recency first, then by
    # severity - Python's sort is stable, so the recency order established
    # by the first pass survives within each severity band after the second.
    alerts.sort(key=lambda a: a["occurred_at"] or "", reverse=True)
    alerts.sort(key=lambda a: _SEVERITY_RANK.get(a["severity"], 9))
    return alerts[:limit]


@router.get("/kpis", summary="Bottom KPI bar (Operations Center)",
            description="Total orders, total customers, total sales, total revenue, "
                        "average order value, and a live count per order_status value.")
def kpi_bar(db: Session = Depends(get_db)):
    total_orders = db.query(func.count(models.OrdersMaster.order_id)).scalar() or 0
    total_customers = (
        db.query(func.count(func.distinct(
            func.coalesce(models.OrdersMaster.customer_id, models.OrdersMaster.mobile)
        ))).scalar() or 0
    )
    total_sales = (
        db.query(func.count(models.OrdersMaster.order_id))
        .filter(models.OrdersMaster.payment_status == PaymentStatus.PAID.value)
        .scalar() or 0
    )
    total_revenue = (
        db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0))
        .filter(models.OrdersMaster.payment_status == PaymentStatus.PAID.value)
        .scalar() or 0.0
    )
    avg_order_value = float(total_revenue) / total_sales if total_sales else 0.0

    status_counts = dict(
        db.query(models.OrdersMaster.order_status, func.count(models.OrdersMaster.order_id))
        .group_by(models.OrdersMaster.order_status)
        .all()
    )

    return {
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_sales": total_sales,
        "total_revenue": round(float(total_revenue), 2),
        "average_order_value": round(avg_order_value, 2),
        "pending_orders": status_counts.get(OrderStatus.RECEIVED.value, 0),
        "preparing_orders": status_counts.get(OrderStatus.PREPARING.value, 0),
        "ready_orders": status_counts.get(OrderStatus.READY.value, 0),
        "out_for_delivery_orders": status_counts.get(OrderStatus.OUT_FOR_DELIVERY.value, 0),
        "delivered_orders": status_counts.get(OrderStatus.DELIVERED.value, 0),
        "cancelled_orders": status_counts.get(OrderStatus.CANCELLED.value, 0),
    }


@router.get("/live-orders", summary="Live orders feed (Operations Center)",
            description="Newest orders first, with customer, items, quantity, amount, "
                        "payment status, order time, and current status.")
def live_orders(limit: int = 25, db: Session = Depends(get_db)):
    orders = (
        db.query(models.OrdersMaster)
        .options(joinedload(models.OrdersMaster.items))
        .order_by(models.OrdersMaster.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for o in orders:
        is_valid, issue = _check_state_validity(o.payment_status, o.order_status)
        result.append({
            "order_id": o.order_id,
            "customer_id": o.customer_id or "-",
            "customer_name": o.customer_name,
            "items": [{"item_name": i.item_name, "quantity": i.quantity} for i in o.items],
            "total_quantity": sum(i.quantity for i in o.items),
            "total_amount": float(o.grand_total),
            "payment_status": o.payment_status,
            "order_time": o.created_at.isoformat() if o.created_at else None,
            "current_status": o.order_status,
            "state_valid": is_valid,
            "state_issue": issue,
        })
    return result


@router.get("/kitchen-ops", summary="Kitchen operations feed (Operations Center)",
            description="Chef, customer, items, preparing/ready state, and time taken "
                        "per kitchen_status row, newest first.")
def kitchen_ops(limit: int = 25, db: Session = Depends(get_db)):
    rows = (
        db.query(models.KitchenStatus, models.OrdersMaster.customer_name)
        .join(models.OrdersMaster, models.KitchenStatus.order_id == models.OrdersMaster.order_id)
        .order_by(models.KitchenStatus.started_at.desc())
        .limit(limit)
        .all()
    )
    now = datetime.utcnow()
    out = []
    for k, customer_name in rows:
        started = k.started_at or now
        is_ready = k.status == KitchenStatus.READY.value
        ended = k.updated_at if is_ready and k.updated_at else now
        time_taken = max(0, int((ended - started).total_seconds()))
        eta_at = None if is_ready else started + timedelta(seconds=settings.SIM_COOKING_SECONDS)
        eta_seconds = (
            None if is_ready
            else max(0, settings.SIM_COOKING_SECONDS - int((now - started).total_seconds()))
        )
        out.append({
            "order_id": k.order_id,
            "chef": k.chef_name,
            "customer": customer_name,
            "item": k.item_assignment,
            "quantity": k.quantity,
            "station_id": k.station_id,
            "is_preparing": k.status == KitchenStatus.COOKING.value,
            "is_ready": is_ready,
            "cooking_status": k.status,
            "time_taken_seconds": time_taken,
            "started_at": k.started_at.isoformat() if k.started_at else None,
            "eta_at": eta_at.isoformat() if eta_at else None,
            "eta_seconds": eta_seconds,
        })
    return out


@router.get("/delivery-ops", summary="Delivery operations feed (Operations Center)",
            description="Delivery partner, customer, order, OTP generated/verified "
                        "(real, derived from status), a display-only simulated OTP code, "
                        "an assigned_at/eta_at pair estimated from the matching kitchen "
                        "row's real READY timestamp (see module docstring), and a "
                        "route-progress fraction for client-side GPS simulation.")
def delivery_ops(limit: int = 25, db: Session = Depends(get_db)):
    rows = (
        db.query(models.DeliveryStatus, models.OrdersMaster.customer_name)
        .join(models.OrdersMaster, models.DeliveryStatus.order_id == models.OrdersMaster.order_id)
        .order_by(models.DeliveryStatus.delivery_id.desc())
        .limit(limit)
        .all()
    )

    # assigned_at has no real column (delivery_status has no timestamps at
    # all) - the consumer dispatches delivery immediately after kitchen
    # completes for the same order/item, so the matching kitchen_status
    # row's real updated_at (its READY timestamp) is the closest real
    # signal for "when this delivery was assigned". Fetched once, keyed by
    # (order_id, item_id), rather than N+1 queries inside the loop below.
    order_ids = {d.order_id for d, _ in rows}
    kitchen_by_key = {}
    if order_ids:
        for k in (
            db.query(models.KitchenStatus)
            .filter(models.KitchenStatus.order_id.in_(order_ids))
            .all()
        ):
            kitchen_by_key[(k.order_id, k.item_id)] = k

    progress_by_status = {
        DeliveryStatus.PENDING.value: 0.0,
        DeliveryStatus.OUT_FOR_DELIVERY.value: 0.55,
        DeliveryStatus.DELIVERED.value: 1.0,
    }
    now = datetime.utcnow()
    out = []
    for d, customer_name in rows:
        otp_generated = d.status in (DeliveryStatus.OUT_FOR_DELIVERY.value, DeliveryStatus.DELIVERED.value)
        otp_verified = d.status == DeliveryStatus.DELIVERED.value

        assigned_at = None
        eta_at = None
        eta_seconds = None
        kitchen_row = kitchen_by_key.get((d.order_id, d.item_id))
        if d.status != DeliveryStatus.PENDING.value and kitchen_row and kitchen_row.updated_at:
            assigned_at = kitchen_row.updated_at
            if d.status == DeliveryStatus.OUT_FOR_DELIVERY.value:
                eta_at = assigned_at + timedelta(seconds=settings.SIM_DELIVERY_SECONDS)
                eta_seconds = max(0, settings.SIM_DELIVERY_SECONDS - int((now - assigned_at).total_seconds()))

        out.append({
            "order_id": d.order_id,
            "delivery_partner": d.delivery_person or "Awaiting Assignment",
            "customer": customer_name,
            "status": d.status,
            "transit_note": d.transit_payload,
            "otp_generated": otp_generated,
            "otp_verified": otp_verified,
            "otp_code": _otp_for_order(d.order_id) if otp_generated else None,
            "route_progress": progress_by_status.get(d.status, 0.0),
            "assigned_at": assigned_at.isoformat() if assigned_at else None,
            "eta_at": eta_at.isoformat() if eta_at else None,
            "eta_seconds": eta_seconds,
        })
    return out


@router.get("/alerts", summary="Business alerts feed (Operations Center)",
            description="Merges inventory low/out-of-stock alerts, failed orders, and "
                        "duplicate-order rejections into one real-time feed, newest first.")
def business_alerts(limit: int = 30, db: Session = Depends(get_db)):
    alerts = []

    for a in (
        db.query(models.InventoryAlert)
        .order_by(models.InventoryAlert.created_at.desc())
        .limit(limit).all()
    ):
        alerts.append({
            "type": a.alert_type or "LOW_STOCK",
            "severity": "HIGH" if (a.alert_type or "") == "OUT_OF_STOCK" else "MEDIUM",
            "message": f"{a.item_name} ({a.item_id}): {a.remaining_stock} left, threshold {a.threshold_value}",
            "occurred_at": a.created_at.isoformat() if a.created_at else None,
        })

    for f in (
        db.query(models.FailedOrder)
        .order_by(models.FailedOrder.failed_at.desc())
        .limit(limit).all()
    ):
        alerts.append({
            "type": "ORDER_FAILED",
            "severity": "HIGH",
            "message": f"Order {f.order_id} failed: {(f.reason or 'unknown reason')[:120]}",
            "occurred_at": f.failed_at.isoformat() if f.failed_at else None,
        })

    for dup in (
        db.query(models.DuplicateOrder)
        .order_by(models.DuplicateOrder.detected_at.desc())
        .limit(limit).all()
    ):
        alerts.append({
            "type": "DUPLICATE_ORDER",
            "severity": "LOW",
            "message": f"Duplicate request rejected (marker {dup.order_id})",
            "occurred_at": dup.detected_at.isoformat() if dup.detected_at else None,
        })

    alerts.sort(key=lambda a: a["occurred_at"] or "", reverse=True)
    return alerts[:limit]


@router.get("/monitoring", summary="Full monitoring snapshot (Monitoring Center)",
            description="Single aggregate endpoint for the Enterprise Monitoring Center "
                        "dashboard: app/database/Kafka/Docker health, DLQ, duplicate/failed "
                        "orders, retry counters, inventory/Kafka/API summaries, and recent "
                        "alerts. Reuses the same checks GET /health and GET /metrics already "
                        "expose, plus direct DB counts - no new health-check logic invented.")
def monitoring_snapshot(db: Session = Depends(get_db)):
    from app.routes import health as health_routes

    db_check = health_routes._check_database(db)
    kafka_check = health_routes._check_kafka_broker()
    disk_check = health_routes._check_disk()
    memory_check = health_routes._check_memory()
    cpu_check = health_routes._check_cpu()
    docker_status = health_routes._check_docker()
    kafka_producer_status = health_routes._check_kafka_producer()
    overall_status = health_routes._compute_overall_status(db_check, kafka_check, disk_check, memory_check, cpu_check)

    snapshot = metrics_module.snapshot()
    counters = snapshot.get("counters", {})
    dlq_summary = get_dlq_summary(db)
    consumer_status = _check_kafka_consumer(kafka_check, counters)

    duplicate_total = db.query(func.count(models.DuplicateOrder.order_id)).scalar() or 0
    recent_duplicates = (
        db.query(models.DuplicateOrder)
        .order_by(models.DuplicateOrder.detected_at.desc()).limit(10).all()
    )
    failed_total = db.query(func.count(models.FailedOrder.order_id)).scalar() or 0
    recent_failed = (
        db.query(models.FailedOrder)
        .order_by(models.FailedOrder.failed_at.desc()).limit(10).all()
    )

    recent_duplicates_out = [
        {"order_id": d.order_id, "transaction_id": d.transaction_id,
         "detected_at": d.detected_at.isoformat() if d.detected_at else None,
         "is_sample": _is_sample_record(d.order_id)}
        for d in recent_duplicates
    ]
    recent_failed_out = [
        {"order_id": f.order_id, "transaction_id": f.transaction_id,
         "reason": f.reason, "failed_at": f.failed_at.isoformat() if f.failed_at else None,
         "is_sample": _is_sample_record(f.order_id)}
        for f in recent_failed
    ]
    dlq_summary["most_recent"] = [
        {**r, "is_sample": _is_sample_record(r.get("order_id"))} for r in dlq_summary["most_recent"]
    ]
    payment_failures = _payment_failures(db)
    kitchen_delay_rows = _kitchen_delays(db)
    low_stock_items = _inventory_by_status(db, "LOW_STOCK")
    out_of_stock_items = _inventory_by_status(db, "OUT_OF_STOCK")

    all_alerts = _monitoring_alerts(
        db, dlq_recent=dlq_summary["most_recent"], failed_recent=recent_failed_out,
        duplicate_recent=recent_duplicates_out, payment_failed_recent=payment_failures["recent"],
        kitchen_delay_rows=kitchen_delay_rows, limit=50,
    )
    critical_alerts = [a for a in all_alerts if a["severity"] == "CRITICAL"]
    active_alerts = [a for a in all_alerts if a["is_active"]]

    total_items = db.query(func.count(models.Inventory.item_id)).scalar() or 0
    low_stock_count = _stock_level_query(db, "LOW_STOCK").count()
    out_of_stock_count = _stock_level_query(db, "OUT_OF_STOCK").count()
    stock_value = (
        db.query(func.coalesce(func.sum(models.Inventory.remaining_stock * models.Inventory.price), 0.0))
        .scalar() or 0.0
    )

    api_summary = {
        "total_requests": counters.get("api_requests_total", 0),
        "requests_4xx": counters.get("api_requests_4xx", 0),
        "requests_5xx": counters.get("api_requests_5xx", 0),
        "endpoints": snapshot.get("api_response_times", {}),
    }

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "application_health": {
            "status": overall_status,
            "environment": settings.APP_ENV,
            "build_version": settings.BUILD_VERSION,
        },
        "database": {
            "status": db_check.get("status"),
            "response_time_ms": db_check.get("response_time_ms"),
            "pool": db_check.get("pool") or get_pool_stats(),
        },
        "kafka": kafka_check,
        "kafka_producer_status": kafka_producer_status,
        "consumer": consumer_status,
        "docker_status": docker_status,
        "dlq": dlq_summary,
        "duplicate_orders": {
            "total": duplicate_total,
            "recent": recent_duplicates_out,
        },
        "failed_orders": {
            "total": failed_total,
            "recent": recent_failed_out,
        },
        "payment_failures": payment_failures,
        "kitchen_delays": {"total": len(kitchen_delay_rows), "recent": kitchen_delay_rows},
        "low_stock_items": low_stock_items,
        "out_of_stock_items": out_of_stock_items,
        "critical_alerts": critical_alerts,
        "active_alerts": active_alerts,
        "retry_queue": {
            "kafka_publish_retry_total": counters.get("kafka_publish_retry_total", 0),
            "kafka_consume_retry_total": counters.get("kafka_consume_retry_total", 0),
        },
        "inventory_summary": {
            "total_items": total_items,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "total_stock_value": round(float(stock_value), 2),
        },
        "kafka_summary": {
            "broker_reachable": kafka_check.get("broker_reachable", False),
            "our_topics_present": kafka_check.get("our_topics_present", {}),
            "publish_success_total": counters.get("kafka_publish_success_total", 0),
            "publish_retry_total": counters.get("kafka_publish_retry_total", 0),
            "publish_dlq_total": counters.get("kafka_publish_dlq_total", 0),
            "consume_success_total": counters.get("kafka_consume_success_total", 0),
            "consume_retry_total": counters.get("kafka_consume_retry_total", 0),
            "consume_dlq_total": counters.get("kafka_consume_dlq_total", 0),
            "processing_time_ms": snapshot.get("kafka_processing_time_ms", {}),
        },
        "api_summary": api_summary,
        "performance": {
            "cpu": cpu_check,
            "memory": memory_check,
            "disk": disk_check,
        },
        "recent_alerts": all_alerts,
    }
