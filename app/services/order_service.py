"""
OMS-360 Enterprise Order Management System - Version 1.1
OrderService - orchestrates order creation by calling the single-
responsibility services below. This file itself now does none of the
direct table manipulation it did in V1 - it locks stock via
InventoryService, creates rows via KitchenService/DeliveryService/
TransactionService, records history via AuditService, and publishes events
via KafkaPublisherService. (V1.1 Requirement #2.)

Atomicity is unchanged from V1: everything from "insert orders_master"
through "insert transactions row" is one SQLAlchemy session / one commit.
The idempotency-duplicate log and the failed-order log are deliberately
separate, later transactions, since they need to persist even though the
main order transaction rolled back.
"""

import time
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.core import metrics
from app.core.enums import AuditEventType, OrderStatus, PaymentStatus, FraudStatus
from app.core.exceptions import (
    OMSBusinessError, DuplicateOrderException, InventoryLockException, UnknownItemException,
)
from app.core.logging_config import get_logger, log_stage, Timer
from app.services import (
    inventory_service, kitchen_service, delivery_service, transaction_service, audit_service,
)
from app.services import kafka_publisher_service as kafka_publisher

logger = get_logger("oms360.services.order_service")

_idempotency_cache: dict = {}

# Re-exported for callers/tests that still import these names from
# order_service (backward compatible with the V1 code).
DuplicateOrderError = DuplicateOrderException
InsufficientStockError = InventoryLockException
UnknownItemError = UnknownItemException


def _generate_order_id() -> str:
    return f"ORD-{uuid.uuid4().hex[:10].upper()}"


def _generate_transaction_id() -> str:
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


def _check_idempotency(idempotency_key: str):
    now = time.time()
    for k in list(_idempotency_cache.keys()):
        if _idempotency_cache[k][1] < now:
            del _idempotency_cache[k]
    cached = _idempotency_cache.get(idempotency_key)
    if cached:
        raise DuplicateOrderException(existing_order_id=cached[0])


def _record_idempotency(idempotency_key: str, order_id: str):
    expires_at = time.time() + settings.DUPLICATE_CACHE_TTL_SECONDS
    _idempotency_cache[idempotency_key] = (order_id, expires_at)


def create_order(db: Session, payload: schemas.OrderCreatePayload, idempotency_key: str = None):
    """Returns the created OrdersMaster row (with .items loaded)."""
    api_timer = Timer()

    if idempotency_key:
        try:
            _check_idempotency(idempotency_key)
        except DuplicateOrderException as dup:
            metrics.increment("duplicate_requests_total")
            marker_order_id = f"DUP-{uuid.uuid4().hex[:10].upper()}"
            try:
                db.add(models.DuplicateOrder(order_id=marker_order_id, transaction_id=idempotency_key))
                db.commit()
            except IntegrityError:
                db.rollback()
            log_stage(marker_order_id, idempotency_key, AuditEventType.DUPLICATE_REJECTED.value,
                      logger=logger, original_order_id=dup.existing_order_id)
            audit_service.record_event(db, marker_order_id, idempotency_key,
                                        AuditEventType.DUPLICATE_REJECTED.value,
                                        details=f"Duplicate of {dup.existing_order_id}")
            raise

    order_id = _generate_order_id()
    transaction_id = _generate_transaction_id()

    with api_timer:
        try:
            order = _create_order_transaction(db, payload, order_id, transaction_id)
        except OMSBusinessError:
            db.rollback()
            metrics.increment("failed_orders_total")
            raise
        except Exception as unexpected_error:
            db.rollback()
            metrics.increment("failed_orders_total")
            _record_failed_order(db, order_id, transaction_id, str(unexpected_error))
            log_stage(order_id, transaction_id, "ORDER_FAILED", logger=logger, error=str(unexpected_error))
            audit_service.record_event(db, order_id, transaction_id, "FAILED", details=str(unexpected_error)[:500])
            logger.exception(f"Unexpected error creating order {order_id}")
            raise

    if idempotency_key:
        _record_idempotency(idempotency_key, order_id)

    metrics.increment("orders_processed_total")
    log_stage(order_id, transaction_id, AuditEventType.ORDER_CREATED.value, logger=logger,
              api_name="create_order", execution_time_ms=api_timer.elapsed_ms,
              customer=payload.customer_name, grand_total=float(order.grand_total))

    kafka_publisher.publish_order_created(
        order_id=order_id, transaction_id=transaction_id, customer_name=payload.customer_name,
        grand_total=float(order.grand_total), items=[i.dict() for i in payload.items],
    )

    return order


def _create_order_transaction(db: Session, payload: schemas.OrderCreatePayload,
                               order_id: str, transaction_id: str):
    """The single atomic unit: stock lock/validate, insert order + items +
    kitchen/delivery/transaction rows, one commit."""
    item_ids = [i.item_id for i in payload.items]
    inventory_by_id = inventory_service.lock_and_fetch(db, item_ids)

    missing = [iid for iid in item_ids if iid not in inventory_by_id]
    if missing:
        raise UnknownItemException(f"Unknown item_id(s): {missing}")

    for line in payload.items:
        stock_row = inventory_by_id[line.item_id]
        if stock_row.remaining_stock < line.quantity:
            raise InventoryLockException(
                f"Insufficient stock for {line.item_id}: "
                f"requested {line.quantity}, available {stock_row.remaining_stock}"
            )

    grand_total = sum(
        float(inventory_by_id[line.item_id].price) * line.quantity
        for line in payload.items
    )

    order = models.OrdersMaster(
        order_id=order_id,
        transaction_id=transaction_id,
        customer_name=payload.customer_name,
        customer_id=payload.customer_id,
        mobile=payload.mobile,
        mobile_number=payload.mobile,
        grand_total=grand_total,
        total_amount=grand_total,
        payment_method=payload.payment_method,
        payment_status=PaymentStatus.PENDING.value,
        fraud_status=FraudStatus.CLEAR.value,
        order_status=OrderStatus.RECEIVED.value,
        live_window_track="SUCCESS_FLOW",
        enterprise_id=payload.enterprise_id,
        door_no=payload.delivery_address.door_no,
        street=payload.delivery_address.street,
        city=payload.delivery_address.city,
        state=payload.delivery_address.state,
        pincode=payload.delivery_address.pincode,
    )
    db.add(order)

    for line in payload.items:
        stock_row = inventory_by_id[line.item_id]

        db.add(models.OrderItem(
            order_id=order_id, item_id=line.item_id, item_name=stock_row.item_name,
            quantity=line.quantity, price=stock_row.price,
        ))

        inventory_service.reserve_stock(db, line.item_id, stock_row, line.quantity, order_id)
        kitchen_service.create_initial_row(db, order_id, transaction_id, line.item_id,
                                            stock_row.item_name, line.quantity)
        delivery_service.create_initial_row(db, order_id, transaction_id, line.item_id, stock_row.item_name)

    transaction_service.create_transaction(db, transaction_id, order_id, payload.payment_method, grand_total)

    db.commit()
    db.refresh(order)

    audit_service.record_event(db, order_id, transaction_id, AuditEventType.ORDER_VALIDATED.value)
    audit_service.record_event(db, order_id, transaction_id, AuditEventType.INVENTORY_RESERVED.value,
                                details=f"{len(payload.items)} line item(s)")

    return order


def _record_failed_order(db: Session, order_id: str, transaction_id: str, reason: str):
    try:
        db.add(models.FailedOrder(order_id=order_id, transaction_id=transaction_id, reason=reason[:1000]))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(f"Also failed to record failed_orders row for {order_id}")
