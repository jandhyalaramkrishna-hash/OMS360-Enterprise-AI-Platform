"""
KafkaPublisherService - single responsibility: knows WHICH topic each
business event goes to and WHAT shape the payload is. app/messaging/producer.py
stays generic (retry/DLQ mechanics only, no business knowledge) - this is
the layer in between, so order_service.py and consumer.py call named
methods like `publish_order_created(...)` instead of building topic names
and dicts inline.
"""

from datetime import datetime

from app.config import settings
from app.messaging.producer import publish_event


def publish_order_created(order_id: str, transaction_id: str, customer_name: str,
                           grand_total: float, items: list) -> bool:
    return publish_event(
        topic=settings.TOPIC_ORDER_CREATED,
        key=order_id,
        value={
            "order_id": order_id,
            "transaction_id": transaction_id,
            "customer_name": customer_name,
            "grand_total": grand_total,
            "items": items,
            "created_at": datetime.utcnow().isoformat(),
        },
    )


def publish_kitchen_accepted(order_id: str) -> bool:
    return publish_event(settings.TOPIC_KITCHEN_ACCEPTED, key=order_id, value={"order_id": order_id})


def publish_delivery_assigned(order_id: str) -> bool:
    return publish_event(settings.TOPIC_DELIVERY_ASSIGNED, key=order_id, value={"order_id": order_id})


def publish_delivery_completed(order_id: str) -> bool:
    return publish_event(settings.TOPIC_DELIVERY_COMPLETED, key=order_id, value={"order_id": order_id})


def publish_payment_completed(order_id: str, transaction_id: str) -> bool:
    return publish_event(
        settings.TOPIC_PAYMENT_COMPLETED, key=order_id,
        value={"order_id": order_id, "transaction_id": transaction_id},
    )


def publish_payment_failed(order_id: str, transaction_id: str, reason: str) -> bool:
    return publish_event(
        settings.TOPIC_PAYMENT_FAILED, key=order_id,
        value={"order_id": order_id, "transaction_id": transaction_id, "reason": reason},
    )


def publish_inventory_updated(item_id: str, remaining_stock: int) -> bool:
    return publish_event(
        settings.TOPIC_INVENTORY_UPDATED, key=item_id,
        value={"item_id": item_id, "remaining_stock": remaining_stock},
    )
