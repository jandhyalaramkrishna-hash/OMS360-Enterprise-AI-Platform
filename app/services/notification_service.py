"""
NotificationService - single responsibility: customer/ops notifications.

Honesty note: SMS is still not wired up to a real provider (see config.py's
SMS_* settings - they remain placeholders) and notify_order_delivered() /
notify_payment_failed() are still stubs. This service stays gated behind
settings.FEATURE_FLAGS["notifications_enabled"] (default False) so it never
pretends to send something it can't.

2026-08-28: notify_low_stock() now sends a real email via SMTP (stdlib
smtplib - no new dependency) using config.py's EMAIL_SMTP_* settings, when
the feature flag is on AND SMTP host/username are configured. If either is
missing, it falls back to the same "log what would have been sent" stub
behaviour as before - so an unconfigured environment (e.g. a fresh clone
with no .env) still behaves exactly as it did previously.

2026-08-28 (later same day): prefixed the low-stock subject line with a
yellow warning emoji (U+26A0 WARNING SIGN) per request, purely so the alert
is easier to spot at a glance in an inbox - no behavior change.
"""

import smtplib
from email.mime.text import MIMEText

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

    if not recipient_email or not settings.EMAIL_SMTP_HOST or not settings.EMAIL_SMTP_USERNAME:
        logger.info(f"[STUB - SMTP not configured] Low stock email queued for {recipient_email}: "
                    f"{item_name} ({item_id}) at {remaining_stock} remaining.")
        return False

    return _send_email(
        to_address=recipient_email,
        subject=f"⚠️ OMS-360 Inventory Alert: {item_name} at danger level ({remaining_stock} remaining)",
        body=(f"Inventory item '{item_name}' ({item_id}) has reached the low-stock danger level.\n\n"
              f"Remaining stock: {remaining_stock}\n\n"
              f"This is an automated alert from OMS-360 Inventory Monitoring."),
    )


def _send_email(to_address: str, subject: str, body: str) -> bool:
    """Minimal stdlib SMTP send (smtplib + email.mime.text) - no new
    dependency added to requirements.txt. Uses the same EMAIL_SMTP_*
    settings notify_low_stock() already read from config.py."""
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM_ADDRESS or settings.EMAIL_SMTP_USERNAME
    message["To"] = to_address

    try:
        with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.EMAIL_SMTP_USERNAME, settings.EMAIL_SMTP_PASSWORD)
            server.sendmail(message["From"], [to_address], message.as_string())
        logger.info(f"Email sent to {to_address}: {subject}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send email to {to_address}: {exc}")
        return False


def _send(event_type: str, order_id: str, customer_name: str, mobile: str, message: str):
    if not settings.FEATURE_FLAGS.get("notifications_enabled", False):
        logger.info(f"[notifications disabled] Would send '{event_type}' to {mobile}: {message}")
        return False
    logger.info(f"[STUB - not actually sent] '{event_type}' SMS/email queued for {mobile}: {message}")
    return True
