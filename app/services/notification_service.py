"""
NotificationService - single responsibility: customer/ops notifications.

Honesty note: there is no real email/SMS provider wired up (see
config.py's EMAIL_*/SMS_* settings - they're placeholders). This service is
gated behind settings.FEATURE_FLAGS["notifications_enabled"] (default
False) specifically so it never pretends to send something it can't.
With the flag off, it logs what WOULD have been sent - useful for demos and
tests, honest about not actually delivering anything.
"""

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("oms360.services.notification_service")


def notify_order_delivered(order_id: str, customer_name: str, mobile: str):
    _send("order_delivered", order_id, customer_name, mobile,
          f"Hi {customer_name}, your order {order_id} has been delivered. Enjoy!")


def notify_payment_failed(order_id: str, customer_name: str, mobile: str, reason: str):
    _send("payment_failed", order_id, customer_name, mobile,
          f"Hi {customer_name}, payment for order {order_id} failed: {reason}")


def notify_low_stock(item_id: str, item_name: str, remaining_stock: int, recipient_email: str):
    if not settings.FEATURE_FLAGS.get("notifications_enabled", False):
        logger.info(f"[notifications disabled] Would alert {recipient_email or '(no recipient configured)'} "
                    f"about low stock: {item_name} ({item_id}) at {remaining_stock} remaining.")
        return False
    logger.info(f"[STUB - not actually sent] Low stock email queued for {recipient_email}: "
                f"{item_name} ({item_id}) at {remaining_stock} remaining.")
    return True


def _send(event_type: str, order_id: str, customer_name: str, mobile: str, message: str):
    if not settings.FEATURE_FLAGS.get("notifications_enabled", False):
        logger.info(f"[notifications disabled] Would send '{event_type}' to {mobile}: {message}")
        return False
    logger.info(f"[STUB - not actually sent] '{event_type}' SMS/email queued for {mobile}: {message}")
    return True
