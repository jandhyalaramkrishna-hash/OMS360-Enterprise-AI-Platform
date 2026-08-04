"""
KitchenService - single responsibility: everything touching `kitchen_status`.
Used by both order_service.py (initial QUEUED rows at order creation) and
messaging/consumer.py (advancing QUEUED -> COOKING -> READY).
"""

from typing import List

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app import models
from app.core.enums import KitchenStatus


def create_initial_row(db: Session, order_id: str, transaction_id: str, item_id: str,
                        item_name: str, quantity: int):
    db.add(models.KitchenStatus(
        order_id=order_id, transaction_id=transaction_id, item_id=item_id,
        item_assignment=item_name, quantity=quantity,
        station_id="UNASSIGNED", status=KitchenStatus.QUEUED.value, chef_name="UNASSIGNED",
    ))


def get_rows_for_order(db: Session, order_id: str) -> List[models.KitchenStatus]:
    return db.query(models.KitchenStatus).filter(models.KitchenStatus.order_id == order_id).all()


def start_cooking(db: Session, rows: List[models.KitchenStatus]):
    for row in rows:
        row.status= KitchenStatus.COOKING.value
        row.station_id = "STATION-AUTO"
        row.chef_name = "Auto-Assigned Chef"
    db.commit()


def complete_cooking(db: Session, rows: List[models.KitchenStatus]):
    for row in rows:
        row.status = KitchenStatus.READY.value
    db.commit()


def get_average_cooking_time_seconds(db: Session) -> float:
    """Backs the dashboard's 'Average Cooking Time' metric. Uses
    started_at -> updated_at on completed (READY) rows as a proxy for
    cooking duration - this project doesn't track a separate
    'cooking_completed_at' column, so updated_at (which changes on every
    row update, including the READY transition) is the best available
    signal without a schema change."""
    result = (
        db.query(func.avg(func.timestampdiff(
            text("SECOND"), models.KitchenStatus.started_at, models.KitchenStatus.updated_at
        )))
        .filter(models.KitchenStatus.status == KitchenStatus.READY.value)
        .scalar()
    )
    return float(result) if result else 0.0
