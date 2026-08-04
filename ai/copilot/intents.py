"""
AI Copilot - Business Intent Catalog
OMS-360 Enterprise Food Delivery Platform

The deterministic core of Business Q&A. Each BUSINESS_INTENTS entry is a
single supported business question: a set of trigger phrases, a real
SQLAlchemy query function (`handler`) reading the same tables
app/routes/dashboard.py already reads (orders_master, order_items,
kitchen_status, delivery_status, inventory, inventory_alerts,
failed_orders, duplicate_orders) via the same models, and pre-written,
human-readable `sql_text`/`related_tables`/`business_flow` metadata used
ONLY by the lazy "View SQL"/"Explain SQL"/"Related Tables"/"Business
Flow" buttons - never shown automatically (per explicit UI requirement).

`sql_text` is a literal, parameter-free description of the query shape
actually executed by `handler` (not a live EXPLAIN or a string built from
untrusted input) - safe to display, and kept next to the handler it
describes so the two can never drift silently apart during a review.

classify_question() is a plain, explainable keyword matcher - no LLM
involved, by design (see ai/copilot/__init__.py's module docstring for
why). Entries are checked in catalog order, so more specific phrasings
are listed before more general ones where they could otherwise collide
(e.g. "out for delivery" before a generic "delivery status").
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.core.enums import DeliveryStatus, FraudStatus, InventoryStatus, KitchenStatus, OrderStatus, PaymentStatus


@dataclass(frozen=True)
class IntentAnswer:
    """What a single intent `handler` returns - the real, computed
    business fact. `value` is the raw number/string a UI could format on
    its own; `answer_text` is a ready-to-display sentence."""

    answer_text: str
    value: object


@dataclass(frozen=True)
class IntentDefinition:
    key: str
    triggers: tuple
    question_example: str
    sql_text: str
    related_tables: tuple
    business_flow: str
    handler: Callable[[Session], IntentAnswer]


def _count_orders_by_status(db: Session, status_value: str) -> int:
    return (
        db.query(func.count(models.OrdersMaster.order_id))
        .filter(models.OrdersMaster.order_status == status_value)
        .scalar()
        or 0
    )


def _h_pending_orders(db: Session) -> IntentAnswer:
    n = _count_orders_by_status(db, OrderStatus.RECEIVED.value)
    return IntentAnswer(f"There {'is' if n == 1 else 'are'} {n} pending order{'' if n == 1 else 's'}.", n)


def _h_preparing_orders(db: Session) -> IntentAnswer:
    n = _count_orders_by_status(db, OrderStatus.PREPARING.value)
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} currently being prepared in the kitchen.", n)


def _h_ready_orders(db: Session) -> IntentAnswer:
    n = _count_orders_by_status(db, OrderStatus.READY.value)
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} ready and waiting for delivery pickup.", n)


def _h_out_for_delivery_orders(db: Session) -> IntentAnswer:
    n = _count_orders_by_status(db, OrderStatus.OUT_FOR_DELIVERY.value)
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} currently out for delivery.", n)


def _h_delivered_orders(db: Session) -> IntentAnswer:
    n = _count_orders_by_status(db, OrderStatus.DELIVERED.value)
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} delivered so far.", n)


def _h_cancelled_orders(db: Session) -> IntentAnswer:
    n = _count_orders_by_status(db, OrderStatus.CANCELLED.value)
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} {'has' if n == 1 else 'have'} been cancelled.", n)


def _h_failed_orders(db: Session) -> IntentAnswer:
    n = db.query(func.count(models.FailedOrder.order_id)).scalar() or 0
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} {'is' if n == 1 else 'are'} recorded as failed.", n)


def _h_duplicate_orders(db: Session) -> IntentAnswer:
    n = db.query(func.count(models.DuplicateOrder.order_id)).scalar() or 0
    return IntentAnswer(f"{n} duplicate order request{'' if n == 1 else 's'} {'has' if n == 1 else 'have'} been rejected.", n)


def _h_total_orders(db: Session) -> IntentAnswer:
    n = db.query(func.count(models.OrdersMaster.order_id)).scalar() or 0
    return IntentAnswer(f"There {'is' if n == 1 else 'are'} {n} order{'' if n == 1 else 's'} in total.", n)


def _h_low_stock_items(db: Session) -> IntentAnswer:
    rows = (
        db.query(models.Inventory.item_name, models.Inventory.remaining_stock)
        .filter(models.Inventory.status == InventoryStatus.LOW_STOCK.value)
        .order_by(models.Inventory.remaining_stock.asc())
        .all()
    )
    n = len(rows)
    if n == 0:
        return IntentAnswer("No items are currently below the low-stock threshold.", 0)
    names = ", ".join(f"{name} ({stock} left)" for name, stock in rows[:5])
    more = f" and {n - 5} more" if n > 5 else ""
    return IntentAnswer(f"{n} item{'' if n == 1 else 's'} below minimum stock: {names}{more}.", n)


def _h_out_of_stock_items(db: Session) -> IntentAnswer:
    n = (
        db.query(func.count(models.Inventory.item_id))
        .filter(models.Inventory.status == InventoryStatus.OUT_OF_STOCK.value)
        .scalar()
        or 0
    )
    return IntentAnswer(f"{n} item{'' if n == 1 else 's'} {'is' if n == 1 else 'are'} completely out of stock.", n)


def _h_inventory_status(db: Session) -> IntentAnswer:
    rows = db.query(models.Inventory.status, func.count(models.Inventory.item_id)).group_by(models.Inventory.status).all()
    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    low = counts.get(InventoryStatus.LOW_STOCK.value, 0)
    out = counts.get(InventoryStatus.OUT_OF_STOCK.value, 0)
    active = counts.get(InventoryStatus.ACTIVE.value, 0)
    inactive = counts.get(InventoryStatus.INACTIVE.value, 0)
    return IntentAnswer(
        f"{total} inventory item{'' if total == 1 else 's'}: {active} in stock, {low} low stock, {out} out of stock"
        f"{f', {inactive} inactive' if inactive else ''}.",
        {"total": total, "active": active, "low_stock": low, "out_of_stock": out, "inactive": inactive},
    )


def _h_inventory_alerts(db: Session) -> IntentAnswer:
    n = db.query(func.count(models.InventoryAlert.alert_id)).scalar() or 0
    return IntentAnswer(f"{n} inventory alert{'' if n == 1 else 's'} recorded.", n)


def _h_todays_sales(db: Session) -> IntentAnswer:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    revenue = (
        db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0))
        .filter(models.OrdersMaster.created_at >= today_start)
        .scalar()
        or 0.0
    )
    count = (
        db.query(func.count(models.OrdersMaster.order_id))
        .filter(models.OrdersMaster.created_at >= today_start)
        .scalar()
        or 0
    )
    return IntentAnswer(
        f"Today: {count} order{'' if count == 1 else 's'}, total sales of ₹{float(revenue):,.2f}.",
        {"orders_today": count, "revenue_today": round(float(revenue), 2)},
    )


def _h_total_revenue(db: Session) -> IntentAnswer:
    revenue = db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0)).scalar() or 0.0
    return IntentAnswer(f"Total revenue across all orders is ₹{float(revenue):,.2f}.", round(float(revenue), 2))


def _h_average_order_value(db: Session) -> IntentAnswer:
    total_orders = db.query(func.count(models.OrdersMaster.order_id)).scalar() or 0
    total_revenue = db.query(func.coalesce(func.sum(models.OrdersMaster.grand_total), 0.0)).scalar() or 0.0
    aov = float(total_revenue) / total_orders if total_orders else 0.0
    return IntentAnswer(f"The average order value is ₹{aov:,.2f}.", round(aov, 2))


def _h_top_selling_item(db: Session) -> IntentAnswer:
    row = (
        db.query(models.OrderItem.item_name, func.sum(models.OrderItem.quantity).label("units"))
        .group_by(models.OrderItem.item_name)
        .order_by(func.sum(models.OrderItem.quantity).desc())
        .first()
    )
    if not row:
        return IntentAnswer("No order items recorded yet, so there is no top-selling item.", None)
    name, units = row
    return IntentAnswer(f"The top-selling item is {name}, with {int(units)} units sold.", {"item_name": name, "units_sold": int(units)})


def _h_kitchen_status(db: Session) -> IntentAnswer:
    cooking = (
        db.query(func.count(models.KitchenStatus.kitchen_id))
        .filter(models.KitchenStatus.status == KitchenStatus.COOKING.value)
        .scalar()
        or 0
    )
    ready = (
        db.query(func.count(models.KitchenStatus.kitchen_id))
        .filter(models.KitchenStatus.status == KitchenStatus.READY.value)
        .scalar()
        or 0
    )
    return IntentAnswer(
        f"Kitchen: {cooking} item{'' if cooking == 1 else 's'} currently cooking, {ready} ready for pickup.",
        {"cooking": cooking, "ready": ready},
    )


def _h_delivery_status(db: Session) -> IntentAnswer:
    pending = (
        db.query(func.count(models.DeliveryStatus.delivery_id))
        .filter(models.DeliveryStatus.status == DeliveryStatus.PENDING.value)
        .scalar()
        or 0
    )
    out = (
        db.query(func.count(models.DeliveryStatus.delivery_id))
        .filter(models.DeliveryStatus.status == DeliveryStatus.OUT_FOR_DELIVERY.value)
        .scalar()
        or 0
    )
    delivered = (
        db.query(func.count(models.DeliveryStatus.delivery_id))
        .filter(models.DeliveryStatus.status == DeliveryStatus.DELIVERED.value)
        .scalar()
        or 0
    )
    return IntentAnswer(
        f"Delivery: {pending} awaiting assignment, {out} out for delivery, {delivered} delivered.",
        {"pending": pending, "out_for_delivery": out, "delivered": delivered},
    )


def _h_total_customers(db: Session) -> IntentAnswer:
    n = (
        db.query(func.count(func.distinct(func.coalesce(models.OrdersMaster.customer_id, models.OrdersMaster.mobile))))
        .scalar()
        or 0
    )
    return IntentAnswer(f"{n} distinct customer{'' if n == 1 else 's'} have placed an order.", n)


def _h_failed_payments(db: Session) -> IntentAnswer:
    n = (
        db.query(func.count(models.OrdersMaster.order_id))
        .filter(models.OrdersMaster.payment_status == PaymentStatus.FAILED.value)
        .scalar()
        or 0
    )
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} {'has' if n == 1 else 'have'} a failed payment.", n)


def _h_fast_moving_items(db: Session) -> IntentAnswer:
    rows = (
        db.query(models.OrderItem.item_name, func.sum(models.OrderItem.quantity).label("units"))
        .group_by(models.OrderItem.item_name)
        .order_by(func.sum(models.OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    if not rows:
        return IntentAnswer("No order items recorded yet, so there are no fast-moving items to rank.", [])
    parts = [{"item_name": name, "units_sold": int(units)} for name, units in rows]
    text = ", ".join(f"{p['item_name']} ({p['units_sold']} sold)" for p in parts)
    return IntentAnswer(f"Fastest-moving items by units sold: {text}.", parts)


def _h_payment_summary(db: Session) -> IntentAnswer:
    rows = db.query(models.OrdersMaster.payment_status, func.count(models.OrdersMaster.order_id)).group_by(models.OrdersMaster.payment_status).all()
    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    if total == 0:
        return IntentAnswer("No orders recorded yet, so there is no payment summary.", {})
    parts = ", ".join(f"{status}: {count}" for status, count in sorted(counts.items(), key=lambda kv: -kv[1]))
    return IntentAnswer(f"Payment summary across {total} order{'' if total == 1 else 's'}: {parts}.", counts)


def _h_fraud_summary(db: Session) -> IntentAnswer:
    rows = db.query(models.OrdersMaster.fraud_status, func.count(models.OrdersMaster.order_id)).group_by(models.OrdersMaster.fraud_status).all()
    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    if total == 0:
        return IntentAnswer("No orders recorded yet, so there is no fraud summary.", {})
    clear = counts.get(FraudStatus.CLEAR.value, 0)
    suspected = counts.get(FraudStatus.SUSPECTED.value, 0)
    blocked = counts.get(FraudStatus.BLOCKED.value, 0)
    return IntentAnswer(
        f"Fraud status across {total} order{'' if total == 1 else 's'}: {clear} clear, {suspected} suspected, {blocked} blocked. "
        "(Note: orders_master.fraud_status is currently set at order creation - there is no automated fraud-detection engine yet; that is a planned future capability, not live scoring.)",
        counts,
    )


def _h_inventory_valuation(db: Session) -> IntentAnswer:
    total_value = db.query(func.coalesce(func.sum(models.Inventory.remaining_stock * models.Inventory.price), 0.0)).scalar() or 0.0
    item_count = db.query(func.count(models.Inventory.item_id)).scalar() or 0
    return IntentAnswer(
        f"Current inventory is valued at ₹{float(total_value):,.2f} across {item_count} item{'' if item_count == 1 else 's'} (remaining stock × price).",
        round(float(total_value), 2),
    )


def _h_dead_letter_queue(db: Session) -> IntentAnswer:
    n = db.query(func.count(models.DlqOrder.order_id)).scalar() or 0
    return IntentAnswer(f"{n} order{'' if n == 1 else 's'} currently in the dead-letter queue.", n)


def _h_recent_alerts(db: Session) -> IntentAnswer:
    rows = (
        db.query(models.InventoryAlert.item_name, models.InventoryAlert.alert_type, models.InventoryAlert.created_at)
        .order_by(models.InventoryAlert.created_at.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return IntentAnswer("No inventory alerts recorded yet.", [])
    parts = [{"item_name": name, "alert_type": atype, "created_at": str(created)} for name, atype, created in rows]
    text = ", ".join(f"{p['item_name']} ({p['alert_type']})" for p in parts)
    return IntentAnswer(f"{len(parts)} most recent alert{'' if len(parts) == 1 else 's'}: {text}.", parts)


def _h_orders_by_customer(db: Session) -> IntentAnswer:
    customer_key = func.coalesce(models.OrdersMaster.customer_id, models.OrdersMaster.mobile)
    rows = (
        db.query(customer_key.label("customer"), func.count(models.OrdersMaster.order_id).label("n"))
        .group_by(customer_key)
        .order_by(func.count(models.OrdersMaster.order_id).desc())
        .limit(5)
        .all()
    )
    if not rows:
        return IntentAnswer("No orders recorded yet, so there is no per-customer breakdown.", [])
    parts = [{"customer": customer, "order_count": int(n)} for customer, n in rows]
    text = ", ".join(f"{p['customer']} ({p['order_count']} order{'' if p['order_count'] == 1 else 's'})" for p in parts)
    return IntentAnswer(f"Top customers by order count: {text}.", parts)


def _h_orders_by_payment_method(db: Session) -> IntentAnswer:
    rows = db.query(models.OrdersMaster.payment_method, func.count(models.OrdersMaster.order_id)).group_by(models.OrdersMaster.payment_method).all()
    counts = {(method or "UNSPECIFIED"): count for method, count in rows}
    total = sum(counts.values())
    if total == 0:
        return IntentAnswer("No orders recorded yet, so there is no payment-method breakdown.", {})
    text = ", ".join(f"{method}: {count}" for method, count in sorted(counts.items(), key=lambda kv: -kv[1]))
    return IntentAnswer(f"Orders by payment method ({total} total): {text}.", counts)


def _h_orders_by_date(db: Session) -> IntentAnswer:
    day = func.date(models.OrdersMaster.created_at)
    rows = db.query(day.label("d"), func.count(models.OrdersMaster.order_id)).group_by(day).order_by(day.desc()).limit(7).all()
    if not rows:
        return IntentAnswer("No orders recorded yet, so there is no by-date breakdown.", [])
    parts = [{"date": str(d), "order_count": int(n)} for d, n in rows]
    text = ", ".join(f"{p['date']}: {p['order_count']}" for p in reversed(parts))
    return IntentAnswer(f"Orders by date (most recent {len(parts)} day{'' if len(parts) == 1 else 's'} with activity): {text}.", parts)


def _h_inventory_ledger(db: Session) -> IntentAnswer:
    rows = db.query(models.InventoryLedger.movement_type, func.count(models.InventoryLedger.ledger_id)).group_by(models.InventoryLedger.movement_type).all()
    counts = {mtype: count for mtype, count in rows}
    total = sum(counts.values())
    if total == 0:
        return IntentAnswer("No inventory ledger entries recorded yet.", {})
    text = ", ".join(f"{mtype}: {count}" for mtype, count in sorted(counts.items(), key=lambda kv: -kv[1]))
    return IntentAnswer(f"{total} inventory ledger entr{'y' if total == 1 else 'ies'}: {text}.", counts)


def _h_kitchen_performance(db: Session) -> IntentAnswer:
    rows = (
        db.query(models.KitchenStatus.started_at, models.KitchenStatus.updated_at)
        .filter(models.KitchenStatus.status == KitchenStatus.READY.value)
        .filter(models.KitchenStatus.started_at.isnot(None))
        .filter(models.KitchenStatus.updated_at.isnot(None))
        .all()
    )
    if not rows:
        return IntentAnswer("No completed kitchen items yet, so there is no average prep time to report.", None)
    durations = [(u - s).total_seconds() for s, u in rows if u and s and u >= s]
    if not durations:
        return IntentAnswer("No completed kitchen items yet, so there is no average prep time to report.", None)
    avg_seconds = sum(durations) / len(durations)
    return IntentAnswer(
        f"Average kitchen prep time across {len(durations)} completed item{'' if len(durations) == 1 else 's'} is "
        f"{avg_seconds:,.0f} seconds (~{avg_seconds / 60:,.1f} min), measured from started_at to the READY update.",
        round(avg_seconds, 1),
    )


def _h_delivery_performance(db: Session) -> IntentAnswer:
    # Honest limitation, not a fabricated number: delivery_status has no
    # started/completed timestamp columns in this schema (see app/models.py),
    # so delivery duration cannot actually be measured yet.
    return IntentAnswer(
        "Delivery duration isn't tracked yet - the delivery_status table has no timestamp columns to measure "
        "how long a delivery takes, only its current status. Kitchen prep time is tracked (see Kitchen Performance); "
        "delivery timing would need started_at/delivered_at columns added to delivery_status first.",
        None,
    )


BUSINESS_INTENTS: tuple = (
    IntentDefinition(
        key="out_for_delivery_orders",
        triggers=("out for delivery",),
        question_example="How many orders are out for delivery?",
        sql_text="SELECT COUNT(*) FROM orders_master WHERE order_status = 'OUT_FOR_DELIVERY';",
        related_tables=("orders_master",),
        business_flow="Order status flips to OUT_FOR_DELIVERY when the kitchen marks an item READY and app/messaging/consumer.py dispatches delivery for it.",
        handler=_h_out_for_delivery_orders,
    ),
    IntentDefinition(
        key="pending_orders",
        triggers=("pending order", "pending orders"),
        question_example="How many pending orders?",
        sql_text="SELECT COUNT(*) FROM orders_master WHERE order_status = 'RECEIVED';",
        related_tables=("orders_master",),
        business_flow="An order stays RECEIVED (pending) from creation (POST /api/v1/orders) until the kitchen consumer picks it up and moves it to PREPARING.",
        handler=_h_pending_orders,
    ),
    IntentDefinition(
        key="preparing_orders",
        triggers=("preparing order", "orders being prepared", "orders are being prepared", "orders in preparation"),
        question_example="How many orders are being prepared?",
        sql_text="SELECT COUNT(*) FROM orders_master WHERE order_status = 'PREPARING';",
        related_tables=("orders_master", "kitchen_status"),
        business_flow="An order moves to PREPARING once app/messaging/consumer.py's kitchen stage starts cooking it (kitchen_status.cooking_status = 'COOKING').",
        handler=_h_preparing_orders,
    ),
    IntentDefinition(
        key="ready_orders",
        triggers=("ready orders", "orders ready", "orders are ready"),
        question_example="How many orders are ready?",
        sql_text="SELECT COUNT(*) FROM orders_master WHERE order_status = 'READY';",
        related_tables=("orders_master", "kitchen_status"),
        business_flow="An order becomes READY when the kitchen finishes cooking (kitchen_status.cooking_status = 'READY'), just before delivery is dispatched.",
        handler=_h_ready_orders,
    ),
    IntentDefinition(
        key="delivered_orders",
        triggers=("delivered order", "orders delivered", "orders have been delivered", "how many delivered"),
        question_example="How many orders have been delivered?",
        sql_text="SELECT COUNT(*) FROM orders_master WHERE order_status = 'DELIVERED';",
        related_tables=("orders_master", "delivery_status"),
        business_flow="An order reaches DELIVERED once delivery_status for every item on the order is marked DELIVERED, completing the order lifecycle.",
        handler=_h_delivered_orders,
    ),
    IntentDefinition(
        key="cancelled_orders",
        triggers=("cancelled order", "canceled order", "orders cancelled", "orders canceled", "orders were cancelled", "orders were canceled"),
        question_example="How many orders were cancelled?",
        sql_text="SELECT COUNT(*) FROM orders_master WHERE order_status = 'CANCELLED';",
        related_tables=("orders_master",),
        business_flow="An order is CANCELLED for a failed/refunded payment or an explicit cancellation - see the state-validity rules in app/routes/dashboard.py.",
        handler=_h_cancelled_orders,
    ),
    IntentDefinition(
        key="failed_orders",
        triggers=("failed order", "failed orders", "show failed orders"),
        question_example="Show failed orders.",
        sql_text="SELECT COUNT(*) FROM failed_orders;",
        related_tables=("failed_orders", "orders_master"),
        business_flow="A row is written to failed_orders when order processing raises an unrecoverable error - see app/services/order_service.py and the DLQ path in app/messaging/consumer.py.",
        handler=_h_failed_orders,
    ),
    IntentDefinition(
        key="duplicate_orders",
        triggers=("duplicate order", "duplicate requests"),
        question_example="How many duplicate orders were rejected?",
        sql_text="SELECT COUNT(*) FROM duplicate_orders;",
        related_tables=("duplicate_orders",),
        business_flow="A duplicate order request (same idempotency key within the TTL window) is rejected before it reaches orders_master and logged to duplicate_orders instead.",
        handler=_h_duplicate_orders,
    ),
    IntentDefinition(
        key="failed_payments",
        triggers=("failed payment", "payment failed", "payments failed"),
        question_example="How many orders have a failed payment?",
        sql_text="SELECT COUNT(*) FROM orders_master WHERE payment_status = 'FAILED';",
        related_tables=("orders_master",),
        business_flow="payment_status is set by app/services/payment_service.py during order processing; FAILED orders may only legitimately be in order_status FAILED or CANCELLED.",
        handler=_h_failed_payments,
    ),
    IntentDefinition(
        key="low_stock_items",
        triggers=("below minimum stock", "low stock", "low-stock"),
        question_example="Which items are below minimum stock?",
        sql_text="SELECT item_name, remaining_stock FROM inventory WHERE status = 'LOW_STOCK' ORDER BY remaining_stock ASC;",
        related_tables=("inventory", "inventory_alerts"),
        business_flow="inventory.status is recalculated by app/services/inventory_service.py on every stock reservation/restock; LOW_STOCK also raises a row in inventory_alerts.",
        handler=_h_low_stock_items,
    ),
    IntentDefinition(
        key="out_of_stock_items",
        triggers=("out of stock", "out-of-stock"),
        question_example="Which items are out of stock?",
        sql_text="SELECT COUNT(*) FROM inventory WHERE status = 'OUT_OF_STOCK';",
        related_tables=("inventory",),
        business_flow="inventory.status becomes OUT_OF_STOCK when remaining_stock reaches zero during stock reservation in app/services/inventory_service.py.",
        handler=_h_out_of_stock_items,
    ),
    IntentDefinition(
        key="inventory_status",
        triggers=("inventory status", "status of the inventory", "stock status", "show inventory status"),
        question_example="What is the inventory status?",
        sql_text="SELECT status, COUNT(*) FROM inventory GROUP BY status;",
        related_tables=("inventory",),
        business_flow="inventory.status is recalculated by app/services/inventory_service.py on every stock reservation/restock - this groups every current item by that status (ACTIVE/LOW_STOCK/OUT_OF_STOCK/INACTIVE).",
        handler=_h_inventory_status,
    ),
    IntentDefinition(
        key="inventory_alerts",
        triggers=("inventory alert", "stock alert"),
        question_example="How many inventory alerts are there?",
        sql_text="SELECT COUNT(*) FROM inventory_alerts;",
        related_tables=("inventory_alerts", "inventory"),
        business_flow="A row is written to inventory_alerts whenever an item crosses into LOW_STOCK or OUT_OF_STOCK, for the Operations/Monitoring dashboards' Business Alerts feed.",
        handler=_h_inventory_alerts,
    ),
    IntentDefinition(
        key="todays_sales",
        triggers=("today's sales", "todays sales", "sales today", "today's revenue", "revenue today"),
        question_example="What are today's sales?",
        sql_text="SELECT COUNT(*), COALESCE(SUM(grand_total),0) FROM orders_master WHERE created_at >= CURRENT_DATE;",
        related_tables=("orders_master",),
        business_flow="Every order's grand_total is written once at creation (POST /api/v1/orders); this sums every order created since midnight UTC.",
        handler=_h_todays_sales,
    ),
    IntentDefinition(
        key="total_revenue",
        triggers=("total revenue", "total sales"),
        question_example="What is the total revenue?",
        sql_text="SELECT COALESCE(SUM(grand_total),0) FROM orders_master;",
        related_tables=("orders_master",),
        business_flow="Sums grand_total across every order ever created, regardless of current status.",
        handler=_h_total_revenue,
    ),
    IntentDefinition(
        key="average_order_value",
        triggers=("average order value", "aov"),
        question_example="What is the average order value?",
        sql_text="SELECT COALESCE(SUM(grand_total),0) / COUNT(*) FROM orders_master;",
        related_tables=("orders_master",),
        business_flow="Total revenue divided by total order count - the same calculation app/routes/dashboard.py's /analytics endpoint already performs.",
        handler=_h_average_order_value,
    ),
    IntentDefinition(
        key="top_selling_item",
        triggers=("top selling item", "top-selling item", "best selling item", "most popular item"),
        question_example="What is the top-selling item?",
        sql_text="SELECT item_name, SUM(quantity) FROM order_items GROUP BY item_name ORDER BY SUM(quantity) DESC LIMIT 1;",
        related_tables=("order_items",),
        business_flow="order_items rows are written once per order line at creation; this aggregates quantity sold per item name across every order.",
        handler=_h_top_selling_item,
    ),
    IntentDefinition(
        key="kitchen_status",
        triggers=("kitchen status", "kitchen queue", "orders in kitchen"),
        question_example="What is the kitchen status?",
        sql_text="SELECT cooking_status, COUNT(*) FROM kitchen_status GROUP BY cooking_status;",
        related_tables=("kitchen_status", "orders_master"),
        business_flow="One kitchen_status row exists per order item; app/messaging/consumer.py moves each row COOKING -> READY as the simulated cook time elapses.",
        handler=_h_kitchen_status,
    ),
    IntentDefinition(
        key="delivery_status",
        triggers=("delivery status", "delivery queue"),
        question_example="What is the delivery status?",
        sql_text="SELECT status, COUNT(*) FROM delivery_status GROUP BY status;",
        related_tables=("delivery_status", "kitchen_status", "orders_master"),
        business_flow="One delivery_status row exists per order item; app/messaging/consumer.py dispatches it (PENDING -> OUT_FOR_DELIVERY) right after the matching kitchen row goes READY.",
        handler=_h_delivery_status,
    ),
    IntentDefinition(
        key="total_customers",
        triggers=("total customers", "how many customers", "number of customers"),
        question_example="How many customers have ordered?",
        sql_text="SELECT COUNT(DISTINCT COALESCE(customer_id, mobile)) FROM orders_master;",
        related_tables=("orders_master",),
        business_flow="Counts distinct customers by customer_id (falling back to mobile number when customer_id is null), the same logic app/routes/dashboard.py's KPI bar uses.",
        handler=_h_total_customers,
    ),
    IntentDefinition(
        key="fast_moving_items",
        triggers=("fast moving item", "fast-moving item", "fastest moving item"),
        question_example="Show fast moving items.",
        sql_text="SELECT item_name, SUM(quantity) FROM order_items GROUP BY item_name ORDER BY SUM(quantity) DESC LIMIT 5;",
        related_tables=("order_items",),
        business_flow="Ranks items by total quantity sold across every order_items row - the same aggregation as top_selling_item, extended to the top 5 instead of just the top 1.",
        handler=_h_fast_moving_items,
    ),
    IntentDefinition(
        key="payment_summary",
        triggers=("payment summary", "summary of payments"),
        question_example="Show payment summary.",
        sql_text="SELECT payment_status, COUNT(*) FROM orders_master GROUP BY payment_status;",
        related_tables=("orders_master",),
        business_flow="payment_status is set by app/services/payment_service.py during order processing (PENDING/PAID/FAILED/REFUNDED); this groups every order by its current value.",
        handler=_h_payment_summary,
    ),
    IntentDefinition(
        key="fraud_summary",
        triggers=("fraud summary", "fraud status", "fraud report"),
        question_example="Show fraud summary.",
        sql_text="SELECT fraud_status, COUNT(*) FROM orders_master GROUP BY fraud_status;",
        related_tables=("orders_master",),
        business_flow="orders_master.fraud_status (CLEAR/SUSPECTED/BLOCKED) is set at order creation. There is no automated fraud-detection engine yet - AI Fraud Detection is a planned V2 roadmap capability (see docs/roadmap/PROJECT-ROADMAP.md), not live scoring today.",
        handler=_h_fraud_summary,
    ),
    IntentDefinition(
        key="inventory_valuation",
        triggers=("inventory valuation", "value of inventory", "stock valuation", "value of stock"),
        question_example="What is the inventory valuation?",
        sql_text="SELECT COALESCE(SUM(remaining_stock * price), 0) FROM inventory;",
        related_tables=("inventory",),
        business_flow="Multiplies each item's remaining_stock by its price and sums across the whole inventory table - the current book value of stock on hand.",
        handler=_h_inventory_valuation,
    ),
    IntentDefinition(
        key="dead_letter_queue",
        triggers=("dead letter queue", "dead-letter queue", "dlq"),
        question_example="Show the dead letter queue.",
        sql_text="SELECT COUNT(*) FROM dlq_orders;",
        related_tables=("dlq_orders",),
        business_flow="A row is written to dlq_orders when a Kafka event exhausts its retry budget without succeeding - see the retry/DLQ path in app/messaging/consumer.py and the Monitoring dashboard's DLQ panel.",
        handler=_h_dead_letter_queue,
    ),
    IntentDefinition(
        key="recent_alerts",
        triggers=("recent alerts", "latest alerts", "show alerts"),
        question_example="Show recent alerts.",
        sql_text="SELECT item_name, alert_type, created_at FROM inventory_alerts ORDER BY created_at DESC LIMIT 5;",
        related_tables=("inventory_alerts",),
        business_flow="Same table inventory_alerts intent reads a count from - this lists the 5 most recent alert rows instead of just counting them.",
        handler=_h_recent_alerts,
    ),
    IntentDefinition(
        key="orders_by_customer",
        triggers=("orders by customer", "orders per customer"),
        question_example="Show orders by customer.",
        sql_text="SELECT COALESCE(customer_id, mobile) AS customer, COUNT(*) FROM orders_master GROUP BY customer ORDER BY COUNT(*) DESC LIMIT 5;",
        related_tables=("orders_master",),
        business_flow="Groups every order by customer_id (falling back to mobile when customer_id is null, same rule as total_customers) and ranks the top 5 by order count.",
        handler=_h_orders_by_customer,
    ),
    IntentDefinition(
        key="orders_by_payment_method",
        triggers=("orders by payment method", "payment method breakdown", "orders by payment"),
        question_example="Show orders by payment method.",
        sql_text="SELECT payment_method, COUNT(*) FROM orders_master GROUP BY payment_method;",
        related_tables=("orders_master",),
        business_flow="payment_method is captured on the order at creation (POST /api/v1/orders); this groups every order by it.",
        handler=_h_orders_by_payment_method,
    ),
    IntentDefinition(
        key="orders_by_date",
        triggers=("orders by date", "orders per day", "daily orders"),
        question_example="Show orders by date.",
        sql_text="SELECT DATE(created_at), COUNT(*) FROM orders_master GROUP BY DATE(created_at) ORDER BY DATE(created_at) DESC LIMIT 7;",
        related_tables=("orders_master",),
        business_flow="Groups every order by the calendar day of created_at, showing the most recent 7 days that actually have orders.",
        handler=_h_orders_by_date,
    ),
    IntentDefinition(
        key="inventory_ledger",
        triggers=("inventory ledger", "stock ledger", "inventory movements"),
        question_example="Show the inventory ledger.",
        sql_text="SELECT movement_type, COUNT(*) FROM inventory_ledger GROUP BY movement_type;",
        related_tables=("inventory_ledger", "inventory"),
        business_flow="One inventory_ledger row is written per stock change (RESTOCK/RESERVE/RELEASE/ADJUSTMENT) by app/services/inventory_service.py - see migrations/003_add_inventory_ledger.sql. This groups every movement by its type.",
        handler=_h_inventory_ledger,
    ),
    IntentDefinition(
        key="kitchen_performance",
        triggers=("kitchen performance", "average prep time", "cooking time", "kitchen speed"),
        question_example="What is the kitchen performance?",
        sql_text="SELECT started_at, updated_at FROM kitchen_status WHERE cooking_status = 'READY';",
        related_tables=("kitchen_status",),
        business_flow="For every kitchen_status row that reached READY, this measures updated_at minus started_at and averages it - an approximation, since updated_at is the row's last-modified time, not a dedicated 'completed_at' column.",
        handler=_h_kitchen_performance,
    ),
    IntentDefinition(
        key="delivery_performance",
        triggers=("delivery performance", "average delivery time", "delivery speed"),
        question_example="What is the delivery performance?",
        sql_text="-- Not measurable: delivery_status has no started_at/completed_at columns in this schema.",
        related_tables=("delivery_status",),
        business_flow="delivery_status only stores current status (PENDING/OUT_FOR_DELIVERY/DELIVERED), not timestamps - so delivery duration cannot be computed without a schema change. See Kitchen Performance for the equivalent, currently-trackable kitchen metric.",
        handler=_h_delivery_performance,
    ),
    # Listed last, not because it is less important, but as a deliberate
    # ordering safeguard: its "how many orders" trigger is intentionally
    # broad (it is meant to catch a bare "how many orders?" with no status
    # qualifier) and would otherwise shadow any earlier, more specific
    # "how many orders <status>?" intent whose own trigger phrase doesn't
    # happen to appear verbatim in a given phrasing. classify_question()
    # checks intents in catalog order and returns on first match, so
    # keeping this last ensures every more-specific intent above always
    # gets first refusal.
    IntentDefinition(
        key="total_orders",
        triggers=("total orders", "how many orders", "number of orders"),
        question_example="How many orders in total?",
        sql_text="SELECT COUNT(*) FROM orders_master;",
        related_tables=("orders_master",),
        business_flow="Every successfully accepted order (POST /api/v1/orders) writes exactly one row to orders_master.",
        handler=_h_total_orders,
    ),
)

_INTENTS_BY_KEY = {i.key: i for i in BUSINESS_INTENTS}


def get_intent(key: str) -> Optional[IntentDefinition]:
    return _INTENTS_BY_KEY.get(key)


def list_supported_questions() -> list:
    return [i.question_example for i in BUSINESS_INTENTS]


def list_intent_catalog() -> list:
    """The full catalog as (key, question_example) pairs, in the same
    catalog order as BUSINESS_INTENTS - powers the "Business Question" and
    "SQL Query" dropdowns, which select by intent key (not free text)."""
    return [{"key": i.key, "question_example": i.question_example} for i in BUSINESS_INTENTS]


def classify_question(question: str) -> Optional[str]:
    """Deterministic, explainable keyword matching - no LLM. Returns the
    matched intent key, or None if nothing matched. Checked in catalog
    order so more specific trigger phrases (listed first) win over more
    general ones that could otherwise also match the same question."""
    normalized = (question or "").strip().lower()
    if not normalized:
        return None
    for intent in BUSINESS_INTENTS:
        for trigger in intent.triggers:
            if trigger in normalized:
                return intent.key
    return None
