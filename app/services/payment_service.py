"""
PaymentService - single responsibility: payment state transitions.
Split out of messaging/consumer.py per V1.1 Requirement #3.

There is no real payment gateway integration in this project (see the
understanding document - payment_method/payment_status are simulated
fields). This service is where a real gateway integration would plug in
later; for now it just marks PAID/FAILED against the DB and delegates
event publishing to KafkaPublisherService.
"""

from sqlalchemy.orm import Session

from app import models
from app.core.enums import OrderStatus, PaymentStatus
from app.core.logging_config import get_logger, log_stage
from app.services import transaction_service, audit_service
from app.services import kafka_publisher_service as kafka_publisher

logger = get_logger("oms360.services.payment_service")


def mark_payment_successful(db: Session, order_id: str, transaction_id: str):
    transaction_service.mark_paid(db, order_id)

    order = db.query(models.OrdersMaster).filter(models.OrdersMaster.order_id == order_id).first()
    if order:
        order.payment_status = PaymentStatus.PAID.value
        db.commit()

    log_stage(order_id, transaction_id, "PAYMENT_SUCCESS", logger=logger)
    audit_service.record_event(db, order_id, transaction_id, "PAYMENT_SUCCESS")
    kafka_publisher.publish_payment_completed(order_id, transaction_id)


def mark_payment_failed(db: Session, order_id: str, transaction_id: str, reason: str):
    transaction_service.mark_failed(db, order_id)

    order = db.query(models.OrdersMaster).filter(models.OrdersMaster.order_id == order_id).first()
    if order:
        order.payment_status = PaymentStatus.FAILED.value
        order.order_status = OrderStatus.FAILED.value
        db.commit()

    log_stage(order_id, transaction_id, "PAYMENT_FAILED", logger=logger, reason=reason)
    audit_service.record_event(db, order_id, transaction_id, "PAYMENT_FAILED", details=reason)
    kafka_publisher.publish_payment_failed(order_id, transaction_id, reason)
