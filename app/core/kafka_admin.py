"""
OMS-360 Enterprise Order Management System - Version 1.1
Kafka observability helpers (Requirement #12): topic stats, DLQ monitoring.
Used by routes/health.py and routes/metrics.py.

Honesty note on consumer lag: computing TRUE lag (high watermark minus last
committed offset) requires either a live Consumer instance with an assigned
partition, or parsing __consumer_offsets - both are more than a stateless
health-check endpoint should do on every request. What's implemented here
is topic/broker visibility via AdminClient, clearly labeled as such. True
per-partition lag would need to be exposed from the running consumer
process itself (app/messaging/consumer.py) rather than computed fresh from
the API process on every health check.
"""

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("oms360.kafka.admin")


def get_topic_stats() -> dict:
    """Returns broker/topic visibility for every topic we care about."""
    try:
        from confluent_kafka.admin import AdminClient
        admin = AdminClient({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
        metadata = admin.list_topics(timeout=3.0)

        our_topics = [
            settings.TOPIC_ORDER_CREATED, settings.TOPIC_PAYMENT_COMPLETED, settings.TOPIC_PAYMENT_FAILED,
            settings.TOPIC_KITCHEN_ACCEPTED, settings.TOPIC_KITCHEN_REJECTED, settings.TOPIC_DELIVERY_ASSIGNED,
            settings.TOPIC_DELIVERY_COMPLETED, settings.TOPIC_INVENTORY_UPDATED, settings.TOPIC_NOTIFICATION_SENT,
            settings.TOPIC_ORDER_DLQ, settings.TOPIC_ORDER_RETRY,
        ]
        return {
            "broker_reachable": True,
            "total_topics_visible": len(metadata.topics),
            "our_topics_present": {t: (t in metadata.topics) for t in our_topics},
        }
    except Exception as exc:
        logger.warning(f"Could not fetch Kafka topic stats: {exc}")
        return {"broker_reachable": False, "error": str(exc)}


def get_dlq_summary(db) -> dict:
    """DLQ monitoring backed by the dlq_orders table - consistent with the
    design decision in messaging/producer.py to route failed
    publishes/consumes to a table rather than a topic no one reads."""
    from app import models
    from sqlalchemy import func

    total = db.query(func.count(models.DlqOrder.order_id)).scalar() or 0
    recent = (
        db.query(models.DlqOrder)
        .order_by(models.DlqOrder.moved_at.desc())
        .limit(5)
        .all()
    )
    return {
        "total_dlq_messages": total,
        "most_recent": [
            {"order_id": r.order_id, "transaction_id": r.transaction_id, "moved_at": str(r.moved_at)}
            for r in recent
        ],
    }
