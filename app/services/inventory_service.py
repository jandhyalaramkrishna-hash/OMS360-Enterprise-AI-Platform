"""
OMS-360 Enterprise Order Management System - Version 1.1
InventoryService - single responsibility: everything touching `inventory`,
`inventory_ledger`, and `inventory_alerts`.

Split out of the old monolithic order_service.py per V1.1 Requirement #2.
order_service.py now calls reserve_stock() instead of touching
models.Inventory rows directly.
"""

import re
from typing import List, Optional

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


def _maybe_raise_alert(db: Session, stock_row: models.Inventory):
    threshold = _get_low_stock_threshold(db)
    if stock_row.remaining_stock <= 0:
        alert_type, status_value = "OUT_OF_STOCK", InventoryStatus.OUT_OF_STOCK.value
    elif stock_row.remaining_stock <= threshold:
        alert_type, status_value = "LOW_STOCK", InventoryStatus.LOW_STOCK.value
    else:
        return

    stock_row.status = status_value
    alert_row = models.InventoryAlert(
        item_id=stock_row.item_id,
        item_name=stock_row.item_name,
        remaining_stock=stock_row.remaining_stock,
        threshold_value=threshold,
        alert_type=alert_type,
        notification_type="EMAIL",
        notification_status="PENDING",
        recipient_email=settings.INVENTORY_ALERT_EMAIL,
    )
    db.add(alert_row)
    logger.warning(f"Inventory alert raised: {alert_type} for {stock_row.item_id} "
                    f"(remaining={stock_row.remaining_stock}, threshold={threshold})")

    # 2026-08-28 addition: fire the existing notify_low_stock() stub for
    # real now (see notification_service.py). Covers both LOW_STOCK and
    # OUT_OF_STOCK - both are "danger level reached" for this alert row,
    # which is exactly what notification_type=EMAIL/notification_status
    # were already modeled for. Never raises - a send failure just leaves
    # notification_status=FAILED on the alert row instead of blocking the
    # surrounding stock reservation/adjustment.
    sent = notification_service.notify_low_stock(
        stock_row.item_id, stock_row.item_name, stock_row.remaining_stock,
        recipient_email=settings.INVENTORY_ALERT_EMAIL,
    )
    alert_row.notification_status = "SENT" if sent else "FAILED"


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
