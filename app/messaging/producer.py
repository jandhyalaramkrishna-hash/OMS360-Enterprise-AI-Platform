"""
OMS-360 Enterprise Order Management System - Version 1.0
The single, authoritative Kafka producer - now with retry + DLQ handling.

Retry: on a failed publish, retries up to settings.MAX_RETRY_COUNT times
with a short backoff (settings.RETRY_DELAY_SECONDS).

Dead-letter handling: if every retry fails, the event is written to the
`dlq_orders` table (using the order_id/transaction_id already present in
the event payload) rather than silently dropped. This satisfies "move
permanently failed messages to your dlq_orders table" directly - going to
the `order.dlq` topic instead isn't used here because dlq_orders has no
consumer of its own defined in this project, and a DB row is easier to
inspect for a QA/demo project than a topic nobody reads.

If Kafka isn't reachable at all (e.g. running the API without Docker), this
logs and returns False instead of crashing the request - a missing broker
should not block order creation in this demo.
"""

import json
import time

from app.config import settings
from app.core.logging_config import get_logger
from app.core import metrics

logger = get_logger("oms360.kafka.producer")

_producer = None


def _get_producer():
    global _producer
    if not settings.KAFKA_ENABLED:
        return None
    if _producer is None:
        try:
            from confluent_kafka import Producer
            _producer = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
        except Exception as exc:
            logger.warning(f"Kafka producer unavailable ({exc}); publishing will be skipped.")
            _producer = False
    return _producer or None


_last_delivery_error = {"error": None}


def _delivery_report(err, msg):
    if err is not None:
        _last_delivery_error["error"] = str(err)
        logger.warning(f"Kafka delivery failed for topic={msg.topic()}: {err}")
    else:
        _last_delivery_error["error"] = None


def publish_event(topic: str, key: str, value: dict) -> bool:
    """Publish `value` to `topic`, keyed by `key`, with retry + DLQ fallback
    on exhaustion. Returns True if ultimately delivered, False otherwise
    (Kafka disabled/unreachable, or all retries exhausted - in which case
    it's already been written to dlq_orders)."""
    producer = _get_producer()
    if producer is None:
        logger.info(f"[Kafka disabled/unavailable] Skipped publish to '{topic}': {value}")
        return False

    last_exc = None
    for attempt in range(1, settings.MAX_RETRY_COUNT + 1):
        try:
            _last_delivery_error["error"] = None
            producer.produce(
                topic=topic, key=str(key),
                value=json.dumps(value, default=str),
                callback=_delivery_report,
            )
            producer.flush(timeout=5.0)
            if _last_delivery_error["error"] is None:
                metrics.increment("kafka_publish_success_total")
                return True
            last_exc = _last_delivery_error["error"]
        except Exception as exc:
            last_exc = str(exc)

        logger.warning(f"Publish attempt {attempt}/{settings.MAX_RETRY_COUNT} to '{topic}' failed: {last_exc}")
        metrics.increment("kafka_publish_retry_total")
        if attempt < settings.MAX_RETRY_COUNT:
            time.sleep(settings.RETRY_DELAY_SECONDS)

    logger.error(f"All {settings.MAX_RETRY_COUNT} publish attempts to '{topic}' failed. Routing to dlq_orders.")
    metrics.increment("kafka_publish_dlq_total")
    _write_to_dlq(topic, key, value, last_exc)
    return False


def _write_to_dlq(topic: str, key: str, value: dict, error: str):
    """Best-effort write to dlq_orders. Imports app.database/app.models
    lazily to avoid a module-level circular import."""
    try:
        from app.database import SessionLocal
        from app import models

        db = SessionLocal()
        try:
            order_id = value.get("order_id") or f"DLQ-{key}"
            db.merge(models.DlqOrder(
                order_id=order_id,
                transaction_id=value.get("transaction_id", str(key)),
                payload=json.dumps({"topic": topic, "value": value, "last_error": error}, default=str),
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception(f"Failed to write DLQ row for topic={topic} key={key} (event is now lost)")


def flush(timeout: float = 5.0):
    producer = _get_producer()
    if producer:
        producer.flush(timeout)
