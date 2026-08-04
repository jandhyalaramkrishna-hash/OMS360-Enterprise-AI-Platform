"""
OMS-360 Enterprise Order Management System - Version 1.1
The single, authoritative Kafka consumer - now a thin orchestrator
(V1.1 Requirement #3). All the actual state-mutation logic lives in the
dedicated services; this file's job is: poll -> parse -> call services in
order -> handle retry/DLQ -> repeat.

Orchestration order: KitchenService -> PaymentService -> DeliveryService ->
AuditService (called by each service internally) -> NotificationService.

Graceful shutdown: SIGTERM/SIGINT sets a flag checked at the top of the
poll loop, so an in-flight message finishes processing before exit instead
of being cut off mid-update.

Run as its own process:
    python -m app.messaging.consumer
"""

import json
import signal
import time

from app.config import settings
from app.database import SessionLocal
from app import models
from app.core import metrics
from app.core.enums import OrderStatus
from app.core.logging_config import get_logger, log_stage, log_kafka_event
from app.messaging.producer import _write_to_dlq
from app.services import kitchen_service, delivery_service, payment_service, notification_service, audit_service
from app.services import kafka_publisher_service as kafka_publisher

logger = get_logger("oms360.kafka.consumer")

_shutdown_requested = False


def _handle_shutdown_signal(signum, frame):
    global _shutdown_requested
    logger.info(f"Received signal {signum}, will shut down after the current message completes.")
    _shutdown_requested = True


def _set_order_status(db, order_id: str, status: str):
    """Keeps orders_master.order_status in sync with the stage the order is
    actually at. Before this fix, order_status was only ever written at
    creation (RECEIVED) and at the very end (DELIVERED) or on payment
    failure (FAILED) - it never reflected PREPARING/READY/OUT_FOR_DELIVERY,
    even though kitchen_status/delivery_status did. That's why the
    dashboard's 'Current Status' column could look stuck on RECEIVED for
    the whole cooking+delivery window. This does not add a new column or
    table - it just writes the existing order_status column at each stage
    the orchestrator already visits."""
    order = db.query(models.OrdersMaster).filter(models.OrdersMaster.order_id == order_id).first()
    if order:
        order.order_status = status
        db.commit()


def _advance_order(order_id: str, transaction_id: str):
    """Orchestrates one order through kitchen -> payment -> delivery.
    Each stage delegates to its own service; this function just sequences
    them and handles the sleep-based simulation timing."""
    db = SessionLocal()
    try:
        kitchen_rows = kitchen_service.get_rows_for_order(db, order_id)
        if not kitchen_rows:
            logger.warning(f"No kitchen_status rows found for {order_id}, skipping.")
            return

        # Payment is confirmed before kitchen prep starts, matching the
        # required valid workflow (PAID -> RECEIVED -> PREPARING -> ...).
        # Previously this call happened AFTER kitchen finished cooking,
        # which meant payment_status stayed PENDING for the entire
        # PREPARING window - a valid-but-confusing combination on the
        # dashboard. (No real payment gateway - see payment_service.py's
        # docstring; this is still a simulated instant-approval.)
        payment_service.mark_payment_successful(db, order_id, transaction_id)

        kitchen_service.start_cooking(db, kitchen_rows)
        _set_order_status(db, order_id, OrderStatus.PREPARING.value)
        log_stage(order_id, transaction_id, "KITCHEN_STARTED", logger=logger)
        audit_service.record_event(db, order_id, transaction_id, "KITCHEN_ASSIGNED")
        audit_service.record_event(db, order_id, transaction_id, "KITCHEN_STARTED")

        time.sleep(settings.SIM_COOKING_SECONDS)

        kitchen_service.complete_cooking(db, kitchen_rows)
        _set_order_status(db, order_id, OrderStatus.READY.value)
        log_stage(order_id, transaction_id, "KITCHEN_COMPLETED", logger=logger)
        audit_service.record_event(db, order_id, transaction_id, "KITCHEN_COMPLETED")
        kafka_publisher.publish_kitchen_accepted(order_id)

        delivery_rows = delivery_service.get_rows_for_order(db, order_id)
        delivery_service.dispatch(db, delivery_rows)
        _set_order_status(db, order_id, OrderStatus.OUT_FOR_DELIVERY.value)
        log_stage(order_id, transaction_id, "OUT_FOR_DELIVERY", logger=logger)
        audit_service.record_event(db, order_id, transaction_id, "DELIVERY_ASSIGNED")
        audit_service.record_event(db, order_id, transaction_id, "OUT_FOR_DELIVERY")
        kafka_publisher.publish_delivery_assigned(order_id)

        time.sleep(settings.SIM_DELIVERY_SECONDS)

        delivery_service.complete_delivery(db, delivery_rows)

        order = db.query(models.OrdersMaster).filter(models.OrdersMaster.order_id == order_id).first()
        if order:
            order.order_status = OrderStatus.DELIVERED.value
            db.commit()
            notification_service.notify_order_delivered(order_id, order.customer_name, order.mobile)

        log_stage(order_id, transaction_id, "DELIVERED", logger=logger)
        audit_service.record_event(db, order_id, transaction_id, "DELIVERED")
        kafka_publisher.publish_delivery_completed(order_id)

    except Exception:
        db.rollback()
        logger.exception(f"Failed to advance order {order_id}")
        raise
    finally:
        db.close()


def _process_message(raw_value: bytes) -> bool:
    start = time.perf_counter()
    try:
        event = json.loads(raw_value.decode("utf-8"))
        order_id = event["order_id"]
        transaction_id = event.get("transaction_id", "")
        logger.info(f"Consumed order.created for {order_id}")
        _advance_order(order_id, transaction_id)
        return True
    finally:
        metrics.record_kafka_processing_time((time.perf_counter() - start) * 1000)


def run_consumer():
    try:
        from confluent_kafka import Consumer
    except ImportError:
        raise SystemExit("confluent_kafka is not installed. Run: pip install confluent-kafka")

    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)

    consumer = Consumer({
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": settings.KAFKA_CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([settings.TOPIC_ORDER_CREATED])
    logger.info(
        f"Consumer started. Listening on '{settings.TOPIC_ORDER_CREATED}' "
        f"at {settings.KAFKA_BOOTSTRAP_SERVERS} (group={settings.KAFKA_CONSUMER_GROUP})"
    )

    try:
        while not _shutdown_requested:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning(f"Kafka error: {msg.error()}")
                continue

            log_kafka_event(
                logger, topic=msg.topic(), offset=msg.offset(),
                consumer_group=settings.KAFKA_CONSUMER_GROUP,
                message=f"Received message at offset {msg.offset()}",
            )

            attempts = 0
            succeeded = False
            last_error = None
            while attempts < settings.MAX_RETRY_COUNT and not succeeded:
                attempts += 1
                try:
                    succeeded = _process_message(msg.value())
                except Exception as exc:
                    last_error = str(exc)
                    logger.warning(f"Processing attempt {attempts}/{settings.MAX_RETRY_COUNT} failed: {exc}")
                    metrics.increment("kafka_consume_retry_total")
                    if attempts < settings.MAX_RETRY_COUNT:
                        time.sleep(settings.RETRY_DELAY_SECONDS)

            if succeeded:
                metrics.increment("kafka_consume_success_total")
            else:
                logger.error(
                    f"Message permanently failed after {settings.MAX_RETRY_COUNT} attempts, "
                    f"routing to dlq_orders: {last_error}"
                )
                metrics.increment("kafka_consume_dlq_total")
                try:
                    event = json.loads(msg.value().decode("utf-8"))
                except Exception:
                    event = {"raw": str(msg.value())}
                _write_to_dlq(settings.TOPIC_ORDER_CREATED, msg.key(), event, last_error)

    finally:
        logger.info("Consumer shutting down.")
        consumer.close()


if __name__ == "__main__":
    run_consumer()
