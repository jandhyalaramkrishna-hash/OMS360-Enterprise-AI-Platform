from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.services import order_service

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post(
    "",
    response_model=schemas.OrderResponse,
    status_code=201,
    summary="Create a new order",
    description=(
        "Creates an order: validates and locks stock, inserts orders_master / "
        "order_items / transactions in one atomic transaction, decrements "
        "inventory, creates initial kitchen_status/delivery_status rows, "
        "records an audit trail entry, and publishes an `order.created` "
        "Kafka event. Pass an `Idempotency-Key` header to make retried "
        "requests safe - a repeat within the TTL window (see "
        "DUPLICATE_CACHE_TTL_SECONDS) returns 409 instead of creating a "
        "second order."
    ),
    responses={
        201: {"description": "Order created."},
        400: {"model": schemas.ErrorResponse, "description": "Unknown item_id or invalid payload."},
        409: {"model": schemas.ErrorResponse, "description": "Insufficient stock, or duplicate request."},
        422: {"model": schemas.ErrorResponse, "description": "Input validation failed (e.g. bad mobile/pincode)."},
    },
)
def create_order(
    payload: schemas.OrderCreatePayload,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(
        default=None, alias="Idempotency-Key",
        description="Optional client-supplied key to make retried requests safe.",
    ),
):
    # Business errors (DuplicateOrderError, InsufficientStockError,
    # UnknownItemError) are all OMSBusinessError subclasses now, so they're
    # caught and formatted consistently by the global handler in
    # app/core/exceptions.py - no per-route try/except translation needed.
    order = order_service.create_order(db, payload, idempotency_key=idempotency_key)
    return order


@router.get(
    "",
    response_model=List[schemas.OrderResponse],
    summary="List recent orders",
    description="Returns the most recent orders (default 50), newest first, with line items.",
)
def list_orders(limit: int = 50, db: Session = Depends(get_db)):
    orders = (
        db.query(models.OrdersMaster)
        .options(joinedload(models.OrdersMaster.items))
        .order_by(models.OrdersMaster.created_at.desc())
        .limit(limit)
        .all()
    )
    return orders


@router.get(
    "/{order_id}",
    response_model=schemas.OrderResponse,
    summary="Get a single order",
    responses={404: {"model": schemas.ErrorResponse, "description": "Order not found."}},
)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = (
        db.query(models.OrdersMaster)
        .options(joinedload(models.OrdersMaster.items))
        .filter(models.OrdersMaster.order_id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get(
    "/{order_id}/audit",
    response_model=List[schemas.AuditEventResponse],
    summary="Get the audit trail for an order",
    description=(
        "Returns every recorded state transition for this order, oldest "
        "first (e.g. ORDER_CREATED, INVENTORY_RESERVED, KITCHEN_STARTED, "
        "KITCHEN_COMPLETED, OUT_FOR_DELIVERY, DELIVERED). Backed by the "
        "order_audit_trail table - see migrations/002_add_audit_trail.sql."
    ),
    responses={404: {"model": schemas.ErrorResponse, "description": "Order not found."}},
)
def get_order_audit_trail(order_id: str, db: Session = Depends(get_db)):
    order_exists = db.query(models.OrdersMaster.order_id).filter(models.OrdersMaster.order_id == order_id).first()
    if not order_exists:
        raise HTTPException(status_code=404, detail="Order not found")

    rows = (
        db.query(models.OrderAuditTrail)
        .filter(models.OrderAuditTrail.order_id == order_id)
        .order_by(models.OrderAuditTrail.created_at.asc())
        .all()
    )
    return rows
