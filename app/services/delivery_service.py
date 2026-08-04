"""
DeliveryService - single responsibility: everything touching `delivery_status`.
"""

from typing import List

from sqlalchemy.orm import Session

from app import models
from app.core.enums import DeliveryStatus


def create_initial_row(db: Session, order_id: str, transaction_id: str, item_id: str, item_name: str):
    db.add(models.DeliveryStatus(
        order_id=order_id, transaction_id=transaction_id, item_id=item_id,
        transit_payload=f"Awaiting kitchen completion for {item_name}",
        status=DeliveryStatus.PENDING.value,
    ))


def get_rows_for_order(db: Session, order_id: str) -> List[models.DeliveryStatus]:
    return db.query(models.DeliveryStatus).filter(models.DeliveryStatus.order_id == order_id).all()


def dispatch(db: Session, rows: List[models.DeliveryStatus]):
    for row in rows:
        row.status = DeliveryStatus.OUT_FOR_DELIVERY.value
        row.delivery_person = "Auto-Assigned Rider"
        row.transit_payload = "Packed and handed off for delivery"
    db.commit()


def complete_delivery(db: Session, rows: List[models.DeliveryStatus]):
    for row in rows:
        row.status = DeliveryStatus.DELIVERED.value
        row.transit_payload = "Delivered to customer"
    db.commit()


def get_average_delivery_time_seconds(db: Session) -> float:
    """`delivery_status` (per oms360_schema.sql, the master schema) has no
    timestamp columns at all - no started_at/dispatched_at/delivered_at.
    There is genuinely no reliable way to compute a real average delivery
    duration without a schema change, which is out of scope unless you
    approve one. Returning 0.0 (and the dashboard route labels this as
    "unavailable") rather than fabricating a number."""
    return 0.0
