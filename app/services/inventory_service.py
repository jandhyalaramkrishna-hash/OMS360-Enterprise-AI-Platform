"""
OMS-360 Enterprise Order Management System - Version 1.1
InventoryService - single responsibility: everything touching `inventory`,
`inventory_ledger`, and `inventory_alerts`.

Split out of the old monolithic order_service.py per V1.1 Requirement #2.
order_service.py now calls reserve_stock() instead of touching
models.Inventory rows directly.
"""

import re
import threading
import time
from typing import List, Optional

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.core.enums import InventoryMovementType, InventoryStatus
from app.core.exceptions import InventoryLockException, InventoryNotFoundException
from app.core.logging_config import get_logger
from app.services import notification_service

logger = get_logger("oms360.services.inventory_service")

DEFAULT_LOW_STOCK_THRESHOLD = 10  # used if system_configuration has no override

# Auto-generated Item Numbers use this pattern (e.g. ITEM-1001). Seed data
# uses word-based ids (ITEM-BURGER, ITEM-SALAD, ...) which never match this
# pattern, so generated ids can never collide with the seeded catalog.
_GENERATED_ITEM_ID_PATTERN = re.compile(r"^ITEM-(\d+)$")
_GENERATED_ITEM_ID_START = 1000

# 2026-11-20 (low-stock email fix): alert emails are no longer sent inside
# the caller's open transaction. _maybe_raise_alert() queues the alert row
# on the Session (db.info[...]); dispatch_pending_notifications() sends the
# queued emails AFTER the caller has committed, so (a) SMTP latency never
# runs while inventory rows are locked FOR UPDATE, and (b) a transaction
# that rolls back can never have already emailed about an alert row that
# no longer exists.
_PENDING_ALERTS_KEY = "oms360_pending_inventory_alerts"
_ALERT_STATUSES = (InventoryStatus.LOW_STOCK.value, InventoryStatus.OUT_OF_STOCK.value)

# alert_id -> time.monotonic() of the last FAILED delivery attempt made by
# automatic processing (see settings.NOTIFICATION_RETRY_COOLDOWN_SECONDS).
_last_failed_attempt = {}
_last_failed_attempt_lock = threading.Lock()


def _get_low_stock_threshold(db: Session) -> int:
    row = (
        db.query(models.SystemConfiguration)
        .filter(models.SystemConfiguration.config_key == "LOW_STOCK_THRESHOLD")
        .first()
    )
    if row and row.config_value.isdigit():
        return int(row.config_value)
    return DEFAULT_LOW_STOCK_THRESHOLD


def lock_and_fetch(db: Session, item_ids: List[str]) -> dict:
    """Locks (SELECT ... FOR UPDATE) and returns {item_id: Inventory row}."""
    rows = (
        db.query(models.Inventory)
        .filter(models.Inventory.item_id.in_(item_ids))
        .with_for_update()
        .all()
    )
    return {row.item_id: row for row in rows}


def reserve_stock(db: Session, item_id: str, stock_row: models.Inventory, quantity: int, order_id: str):
    """Decrements stock for one line item, writes a ledger row, and raises/
    creates a low-stock alert if the threshold is crossed. Caller owns the
    surrounding transaction/commit."""
    if stock_row.remaining_stock < quantity:
        raise InventoryLockException(
            f"Insufficient stock for {item_id}: requested {quantity}, available {stock_row.remaining_stock}"
        )

    stock_row.remaining_stock -= quantity
    stock_row.used_stock += quantity

    _write_ledger(db, item_id, InventoryMovementType.RESERVE, -quantity,
                  stock_row.remaining_stock, reference_order_id=order_id, reason="Order reservation")

    _maybe_raise_alert(db, stock_row)


def release_stock(db: Session, item_id: str, stock_row: models.Inventory, quantity: int, order_id: str, reason: str):
    """Used for cancellations/refunds - puts stock back."""
    stock_row.remaining_stock += quantity
    stock_row.used_stock = max(0, stock_row.used_stock - quantity)
    _write_ledger(db, item_id, InventoryMovementType.RELEASE, quantity,
                  stock_row.remaining_stock, reference_order_id=order_id, reason=reason)
    _recover_status_if_cleared(db, stock_row)


def restock(db: Session, item_id: str, quantity: int, reason: str = "Manual restock") -> models.Inventory:
    if quantity <= 0:
        raise ValueError("Restock quantity must be positive")

    stock_row = (
        db.query(models.Inventory)
        .filter(models.Inventory.item_id == item_id)
        .with_for_update()
        .first()
    )
    if not stock_row:
        raise InventoryNotFoundException(f"No inventory row for item_id={item_id}")

    stock_row.remaining_stock += quantity
    stock_row.total_stock += quantity
    if stock_row.status == InventoryStatus.OUT_OF_STOCK.value:
        stock_row.status = InventoryStatus.ACTIVE.value
    _recover_status_if_cleared(db, stock_row)

    _write_ledger(db, item_id, InventoryMovementType.RESTOCK, quantity,
                  stock_row.remaining_stock, reference_order_id=None, reason=reason)

    db.commit()
    db.refresh(stock_row)
    logger.info(f"Restocked {item_id} by {quantity}, new remaining_stock={stock_row.remaining_stock}")
    return stock_row


def _generate_item_id(db: Session) -> str:
    """Auto-generates the next ITEM-NNNN Item Number for "Add New Item".
    Scans the existing inventory table for the highest ITEM-<digits> id
    already in use and returns the next one, retrying past any unlikely
    collision (e.g. a row inserted concurrently)."""
    highest = _GENERATED_ITEM_ID_START
    for (existing_id,) in db.query(models.Inventory.item_id).all():
        match = _GENERATED_ITEM_ID_PATTERN.match(existing_id or "")
        if match:
            highest = max(highest, int(match.group(1)))

    candidate_n = highest + 1
    candidate = f"ITEM-{candidate_n:04d}"
    while db.query(models.Inventory.item_id).filter(models.Inventory.item_id == candidate).first():
        candidate_n += 1
        candidate = f"ITEM-{candidate_n:04d}"
    return candidate


def create_item(db: Session, item_name: str, price: float, total_stock: int,
                 status: str = None) -> models.Inventory:
    """Backs POST /api/v1/inventory - the Inventory Dashboard's "Add New
    Item" dialog. Auto-generates the Item Number, writes matching rows to
    BOTH `items` and `inventory` (see app/models.py - the two tables are
    structurally identical and kept mirrored) and one inventory_ledger
    row (movement_type=RESTOCK) recording the item's starting stock, so
    the new item is immediately visible on the Dashboard and to AI
    Copilot (both read `inventory`) with a full audit trail from the
    moment it exists. category/unit are intentionally left NULL here -
    see InventoryCreateRequest's docstring in app/schemas.py."""
    item_id = _generate_item_id(db)
    status_value = status or InventoryStatus.ACTIVE.value

    inventory_row = models.Inventory(
        item_id=item_id, item_name=item_name, price=price,
        total_stock=total_stock, remaining_stock=total_stock, used_stock=0,
        status=status_value,
    )
    item_row = models.Item(
        item_id=item_id, item_name=item_name, price=price,
        total_stock=total_stock, remaining_stock=total_stock, used_stock=0,
        status=status_value,
    )
    db.add(inventory_row)
    db.add(item_row)

    if total_stock > 0:
        _write_ledger(db, item_id, InventoryMovementType.RESTOCK, total_stock,
                      total_stock, reference_order_id=None,
                      reason="Initial stock - item created via Inventory Dashboard")

    db.commit()
    db.refresh(inventory_row)
    logger.info(f"Created new inventory item {item_id} ({item_name}), starting stock={total_stock}")
    return inventory_row


def update_item(db: Session, item_id: str, price: float = None, status: str = None,
                 item_name: str = None, stock: Optional[int] = None,
                 category: Optional[str] = None, unit: Optional[str] = None) -> models.Inventory:
    """Backs PUT /api/v1/inventory/{item} - the Inventory Dashboard's
    "Update Inventory" dialog. price/status/item_name/category/unit are
    simple field updates. `stock`, if given, is an ADMIN CORRECTION of
    remaining_stock (not a delta) - kept ledgered (movement_type=ADJUSTMENT)
    exactly like every other stock change, and total_stock is shifted by
    the same delta so total_stock stays >= remaining_stock. If `status` is
    not explicitly given but `stock` is, status is recalculated from the
    new stock level the same way order reservations recalculate it
    (_maybe_raise_alert) - so a manual stock correction can't leave a
    stale ACTIVE/LOW_STOCK/OUT_OF_STOCK chip behind. Also mirrors
    item_name/price/status/stock/category/unit onto the matching `items`
    row (if one exists) - see app/models.py, `items` and `inventory` are
    kept structurally in sync.

    2026-07-27 addition (see docs/governance/DECISION-LOG.md): `category`
    and `unit` are new optional fields backed by the nullable
    `category`/`unit` columns added in
    migrations/004_add_item_category_unit.sql. They follow the same
    "None means leave unchanged" convention as price/status/item_name -
    only touched when the caller actually supplies a value."""
    stock_row = (
        db.query(models.Inventory)
        .filter(models.Inventory.item_id == item_id)
        .with_for_update()
        .first()
    )
    if not stock_row:
        raise InventoryNotFoundException(f"No inventory row for item_id={item_id}")

    if price is not None:
        stock_row.price = price
    if item_name is not None:
        stock_row.item_name = item_name
    if category is not None:
        stock_row.category = category
    if unit is not None:
        stock_row.unit = unit

    if stock is not None and stock != stock_row.remaining_stock:
        delta = stock - stock_row.remaining_stock
        stock_row.remaining_stock = stock
        stock_row.total_stock = max(stock_row.total_stock + delta, stock)
        _write_ledger(db, item_id, InventoryMovementType.ADJUSTMENT, delta, stock_row.remaining_stock,
                      reference_order_id=None, reason="Manual stock adjustment via Inventory Dashboard")
        if status is not None:
            stock_row.status = status
        else:
            _recompute_status_from_stock(db, stock_row)
    elif status is not None:
        stock_row.status = status

    db.commit()
    db.refresh(stock_row)

    item_row = db.query(models.Item).filter(models.Item.item_id == item_id).first()
    if item_row:
        item_row.item_name = stock_row.item_name
        item_row.price = stock_row.price
        item_row.status = stock_row.status
        item_row.total_stock = stock_row.total_stock
        item_row.remaining_stock = stock_row.remaining_stock
        item_row.used_stock = stock_row.used_stock
        item_row.category = stock_row.category
        item_row.unit = stock_row.unit
        db.commit()

    # Alert emails (if a stock correction raised one) go out only after the
    # update above is committed. Never raises.
    dispatch_pending_notifications(db)

    logger.info(f"Updated inventory item {item_id} (price={price}, status={status}, "
                f"item_name={item_name}, stock={stock}, category={category}, unit={unit})")
    return stock_row


def get_low_stock(db: Session) -> List[models.Inventory]:
    threshold = _get_low_stock_threshold(db)
    return (
        db.query(models.Inventory)
        .filter(models.Inventory.remaining_stock > 0, models.Inventory.remaining_stock <= threshold)
        .order_by(models.Inventory.remaining_stock.asc())
        .all()
    )


def get_out_of_stock(db: Session) -> List[models.Inventory]:
    return db.query(models.Inventory).filter(models.Inventory.remaining_stock <= 0).all()


def get_alerts(db: Session, limit: int = 50) -> List[models.InventoryAlert]:
    return (
        db.query(models.InventoryAlert)
        .order_by(models.InventoryAlert.created_at.desc())
        .limit(limit)
        .all()
    )


def get_ledger_history(db: Session, item_id: str = None, limit: int = 100) -> List[models.InventoryLedger]:
    """Backs GET /api/v1/inventory/history - also the raw data source for
    consumption/usage reporting (aggregate in the route layer)."""
    query = db.query(models.InventoryLedger)
    if item_id:
        query = query.filter(models.InventoryLedger.item_id == item_id)
    # Tie-break on ledger_id (not just created_at) so two ledger rows written
    # within the same second - e.g. "Add New Item" immediately followed by an
    # "Update Inventory" stock correction - still come back newest-first.
    return (
        query.order_by(models.InventoryLedger.created_at.desc(), models.InventoryLedger.ledger_id.desc())
        .limit(limit)
        .all()
    )


def _write_ledger(db: Session, item_id: str, movement_type: InventoryMovementType,
                   quantity_change: int, remaining_after: int, reference_order_id: str, reason: str):
    db.add(models.InventoryLedger(
        item_id=item_id,
        movement_type=movement_type.value,
        quantity_change=quantity_change,
        remaining_stock_after=remaining_after,
        reference_order_id=reference_order_id,
        reason=reason,
    ))


def _classify_stock_level(stock_row: models.Inventory, threshold: int):
    """(alert_type, status_value) for a depleted row, or None if above threshold."""
    if stock_row.remaining_stock <= 0:
        return "OUT_OF_STOCK", InventoryStatus.OUT_OF_STOCK.value
    if stock_row.remaining_stock <= threshold:
        return "LOW_STOCK", InventoryStatus.LOW_STOCK.value
    return None


def _latest_alert(db: Session, item_id: str) -> Optional[models.InventoryAlert]:
    return (
        db.query(models.InventoryAlert)
        .filter(models.InventoryAlert.item_id == item_id)
        .order_by(models.InventoryAlert.alert_id.desc())
        .first()
    )


def _queue_for_dispatch(db: Session, alert_row: models.InventoryAlert):
    queued = db.info.setdefault(_PENDING_ALERTS_KEY, [])
    if not any(existing is alert_row for existing in queued):
        queued.append(alert_row)


def _maybe_raise_alert(db: Session, stock_row: models.Inventory):
    """Flags a depleted row LOW_STOCK/OUT_OF_STOCK and records an
    inventory_alerts row with notification_status=PENDING, queued for email
    delivery after the caller commits (dispatch_pending_notifications()).

    2026-11-20 de-duplication: a new alert row (and email) is only created
    when the item ENTERS a danger state - ACTIVE/INACTIVE -> LOW_STOCK,
    anything -> OUT_OF_STOCK, OUT_OF_STOCK -> LOW_STOCK. If the item was
    already in that state and its latest alert is of the same type, that
    same alert is reused: if it was already SENT nothing more happens (no
    duplicate email per order); if it is still PENDING/FAILED it is queued
    again so a previously undelivered alert is retried. Previously every
    reservation below the threshold inserted another alert row and sent
    another email."""
    threshold = _get_low_stock_threshold(db)
    level = _classify_stock_level(stock_row, threshold)
    if level is None:
        return None
    alert_type, status_value = level

    previous_status = stock_row.status
    stock_row.status = status_value

    # Same item depleted twice inside one not-yet-committed transaction
    # (e.g. one order listing the same item on two lines): reuse the alert
    # already queued on this Session - SessionLocal has autoflush=False, so
    # it would not be visible to the query below yet.
    for queued in db.info.get(_PENDING_ALERTS_KEY, []):
        if queued.item_id == stock_row.item_id and queued.alert_type == alert_type:
            return queued

    if previous_status == status_value:
        latest = _latest_alert(db, stock_row.item_id)
        if latest is not None and latest.alert_type == alert_type:
            if latest.notification_status != notification_service.STATUS_SENT:
                _queue_for_dispatch(db, latest)
            logger.info(f"Inventory alert {alert_type} for {stock_row.item_id} already open "
                        f"(alert_id={latest.alert_id}, notification_status={latest.notification_status}) "
                        f"- no duplicate alert created.")
            return latest

    alert_row = models.InventoryAlert(
        item_id=stock_row.item_id,
        item_name=stock_row.item_name,
        remaining_stock=stock_row.remaining_stock,
        threshold_value=threshold,
        alert_type=alert_type,
        notification_type="EMAIL",
        notification_status=notification_service.STATUS_PENDING,
        recipient_email=settings.INVENTORY_ALERT_EMAIL,
    )
    db.add(alert_row)
    _queue_for_dispatch(db, alert_row)
    logger.warning(f"Inventory alert raised: {alert_type} for {stock_row.item_id} "
                    f"(remaining={stock_row.remaining_stock}, threshold={threshold})")
    return alert_row


def _in_failed_cooldown(alert_id: int) -> bool:
    with _last_failed_attempt_lock:
        last = _last_failed_attempt.get(alert_id)
    return last is not None and (time.monotonic() - last) < settings.NOTIFICATION_RETRY_COOLDOWN_SECONDS


def _deliver_alert(db: Session, alert_row: models.InventoryAlert, respect_cooldown: bool) -> Optional[str]:
    """Sends one alert email and persists the outcome. Returns the new
    notification_status, or None if skipped (already SENT / in cooldown)."""
    if alert_row.notification_status == notification_service.STATUS_SENT:
        return None
    if (respect_cooldown and alert_row.notification_status == notification_service.STATUS_FAILED
            and _in_failed_cooldown(alert_row.alert_id)):
        logger.info(f"Alert {alert_row.alert_id} email retry skipped (FAILED recently, cooldown active).")
        return None

    # Deliver to the currently configured recipient; record it on the row
    # so inventory_alerts.recipient_email shows where the email really went.
    recipient = (settings.INVENTORY_ALERT_EMAIL or alert_row.recipient_email or "").strip()
    status = notification_service.send_low_stock_alert(
        alert_row.item_id, alert_row.item_name, alert_row.remaining_stock, recipient,
        alert_type=alert_row.alert_type or "LOW_STOCK", threshold=alert_row.threshold_value,
    )
    with _last_failed_attempt_lock:
        if status == notification_service.STATUS_FAILED:
            _last_failed_attempt[alert_row.alert_id] = time.monotonic()
        else:
            _last_failed_attempt.pop(alert_row.alert_id, None)

    alert_row.notification_status = status
    if recipient and alert_row.recipient_email != recipient:
        alert_row.recipient_email = recipient
    db.commit()
    return status


def dispatch_pending_notifications(db: Session, respect_cooldown: bool = True) -> dict:
    """Sends every alert email queued on this Session by _maybe_raise_alert().
    Must be called AFTER the caller's db.commit(). Never raises - a failure
    only leaves notification_status=FAILED (or PENDING if notifications are
    disabled) on the alert row."""
    queued = db.info.pop(_PENDING_ALERTS_KEY, [])
    summary = {"attempted": 0, "sent": 0, "failed": 0, "pending": 0, "skipped": 0, "alerts": []}
    for alert_row in queued:
        try:
            if not sa_inspect(alert_row).persistent:
                continue  # its transaction was rolled back - nothing to notify about
            status = _deliver_alert(db, alert_row, respect_cooldown)
        except Exception:
            logger.exception("Failed to dispatch inventory alert notification")
            db.rollback()
            continue
        if status is None:
            summary["skipped"] += 1
            continue
        summary["attempted"] += 1
        summary[status.lower()] += 1
        summary["alerts"].append({
            "alert_id": alert_row.alert_id, "item_id": alert_row.item_id,
            "alert_type": alert_row.alert_type, "notification_status": status,
        })
    return summary


def dispatch_open_alerts(db: Session) -> dict:
    """Backs POST /api/v1/inventory/alerts/dispatch-pending. For every item
    that is CURRENTLY low/out of stock, (re)sends its latest alert if that
    alert matches the item's current level and was never SENT. This is how
    alerts recorded while notifications were disabled (or while SMTP was
    failing) get delivered without waiting for the stock to change again.
    Never creates alert rows and never touches inventory rows. Ignores the
    automatic-retry cooldown."""
    threshold = _get_low_stock_threshold(db)
    rows = (
        db.query(models.Inventory)
        .filter(models.Inventory.remaining_stock <= threshold)
        .order_by(models.Inventory.item_id)
        .all()
    )
    for stock_row in rows:
        level = _classify_stock_level(stock_row, threshold)
        latest = _latest_alert(db, stock_row.item_id)
        if (level and latest is not None and latest.alert_type == level[0]
                and latest.notification_status != notification_service.STATUS_SENT):
            _queue_for_dispatch(db, latest)
    return dispatch_pending_notifications(db, respect_cooldown=False)


def _recover_status_if_cleared(db: Session, stock_row: models.Inventory):
    """Restock/release: once stock is back above the threshold, a LOW_STOCK/
    OUT_OF_STOCK row returns to ACTIVE, so the next depletion is treated as
    a new alert episode (and emailed) instead of being de-duplicated."""
    if stock_row.status in _ALERT_STATUSES and stock_row.remaining_stock > _get_low_stock_threshold(db):
        stock_row.status = InventoryStatus.ACTIVE.value


def _recompute_status_from_stock(db: Session, stock_row: models.Inventory):
    """Used only by update_item()'s manual stock-correction path. Unlike
    _maybe_raise_alert() (which only ever moves a row INTO LOW_STOCK/
    OUT_OF_STOCK during order reservation, matching that flow's one-way
    depletion), a manual correction can also move stock back UP - so this
    additionally recovers to ACTIVE when the corrected stock clears the
    threshold, the same recovery restock() already does for the
    OUT_OF_STOCK case."""
    threshold = _get_low_stock_threshold(db)
    if stock_row.remaining_stock <= 0:
        _maybe_raise_alert(db, stock_row)
    elif stock_row.remaining_stock <= threshold:
        _maybe_raise_alert(db, stock_row)
    else:
        stock_row.status = InventoryStatus.ACTIVE.value
