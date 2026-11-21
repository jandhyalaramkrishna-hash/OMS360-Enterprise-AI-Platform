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

2026-11-20 fix (Low Stock Email Notification defect):
  - Added send_low_stock_alert(), which returns an accurate delivery
    outcome instead of a bare bool:
        PENDING - notifications_enabled is off, so nothing was attempted.
                  The alert stays eligible to be sent once the flag is on.
        SENT    - the SMTP server accepted the message.
        FAILED  - delivery was attempted and did not succeed (SMTP config
                  incomplete, connection/TLS error, authentication
                  rejected, recipient refused, ...).
    Previously every not-sent case (including "feature disabled") was
    collapsed into False and stored as FAILED, so a disabled-then-re-enabled
    environment could not tell "never attempted" from "Gmail rejected the
    login", and nothing ever retried either.
  - notify_low_stock() is kept with its original signature/bool return for
    backward compatibility; it now delegates to send_low_stock_alert().
  - OUT_OF_STOCK alerts now get their own subject/body wording.
  - SMTP failures are classified (auth / recipient refused / connection)
    and logged WITHOUT credentials. The password is never logged; the
    username is masked.
  - Surrounding whitespace / stray CR from a CRLF .env is trimmed from the
    SMTP password before login.
"""

import json
import smtplib
import socket
import urllib.error
import urllib.request
from email.mime.text import MIMEText

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("oms360.services.notification_service")

# notification_status values stored on inventory_alerts (varchar(20) -
# existing column, no schema change).
STATUS_PENDING = "PENDING"
STATUS_SENT = "SENT"
STATUS_FAILED = "FAILED"


def notify_order_delivered(order_id: str, customer_name: str, mobile: str):
    _send("order_delivered", order_id, customer_name, mobile,
          f"Hi {customer_name}, your order {order_id} has been delivered. Enjoy!")


def notify_payment_failed(order_id: str, customer_name: str, mobile: str, reason: str):
    _send("payment_failed", order_id, customer_name, mobile,
          f"Hi {customer_name}, payment for order {order_id} failed: {reason}")


def notify_low_stock(item_id: str, item_name: str, remaining_stock: int, recipient_email: str,
                     alert_type: str = "LOW_STOCK", threshold: int = None) -> bool:
    """Backward-compatible wrapper: True only when the email was actually sent."""
    return send_low_stock_alert(item_id, item_name, remaining_stock, recipient_email,
                                alert_type=alert_type, threshold=threshold) == STATUS_SENT


def send_low_stock_alert(item_id: str, item_name: str, remaining_stock: int, recipient_email: str,
                         alert_type: str = "LOW_STOCK", threshold: int = None) -> str:
    """Sends one inventory alert email. Never raises. Returns PENDING/SENT/FAILED."""
    if not settings.FEATURE_FLAGS.get("notifications_enabled", False):
        logger.info(f"[notifications disabled] {alert_type} alert for {item_name} ({item_id}) "
                    f"at {remaining_stock} remaining left PENDING - not sent.")
        return STATUS_PENDING

    provider = (settings.EMAIL_PROVIDER or "smtp").strip().lower()
    if provider == "brevo":
        required = (
            ("OMS360_INVENTORY_ALERT_EMAIL (recipient)", recipient_email),
            ("OMS360_BREVO_API_KEY", settings.BREVO_API_KEY),
            ("OMS360_EMAIL_FROM (verified Brevo sender)", settings.EMAIL_FROM_ADDRESS),
        )
    elif provider == "smtp":
        required = (
            ("OMS360_INVENTORY_ALERT_EMAIL (recipient)", recipient_email),
            ("OMS360_EMAIL_SMTP_HOST", settings.EMAIL_SMTP_HOST),
            ("OMS360_EMAIL_SMTP_USERNAME", settings.EMAIL_SMTP_USERNAME),
            ("OMS360_EMAIL_SMTP_PASSWORD", settings.EMAIL_SMTP_PASSWORD),
        )
    else:
        logger.error(f"Inventory alert email NOT sent for {item_id}: unknown OMS360_EMAIL_PROVIDER "
                     f"'{provider}' (expected 'smtp' or 'brevo').")
        return STATUS_FAILED

    missing = [name for name, value in required if not (value or "").strip()]
    if missing:
        logger.error(f"Inventory alert email NOT sent for {item_id}: {provider.upper()} configuration "
                     f"incomplete (missing: {', '.join(missing)}).")
        return STATUS_FAILED

    subject, body = _build_alert_message(item_id, item_name, remaining_stock, alert_type, threshold)
    sender = _send_via_brevo if provider == "brevo" else _send_email
    return STATUS_SENT if sender(recipient_email.strip(), subject, body) else STATUS_FAILED


def _build_alert_message(item_id, item_name, remaining_stock, alert_type, threshold):
    threshold_line = (f"Low-stock rule: alert when remaining stock is below {threshold}\n"
                      if threshold is not None else "")
    if alert_type == "OUT_OF_STOCK":
        subject = f"⚠️ OMS-360 Inventory Alert: {item_name} is OUT OF STOCK"
        headline = f"Inventory item '{item_name}' ({item_id}) is out of stock."
    else:
        subject = f"⚠️ OMS-360 Inventory Alert: {item_name} at danger level ({remaining_stock} remaining)"
        headline = f"Inventory item '{item_name}' ({item_id}) has reached the low-stock danger level."
    body = (f"{headline}\n\n"
            f"Alert type: {alert_type}\n"
            f"Remaining stock: {remaining_stock}\n"
            f"{threshold_line}\n"
            f"This is an automated alert from OMS-360 Inventory Monitoring.")
    return subject, body


def _mask(address: str) -> str:
    if not address or "@" not in address:
        return "***"
    local, domain = address.split("@", 1)
    return f"{local[:2]}***@{domain}"


def _send_email(to_address: str, subject: str, body: str) -> bool:
    """Minimal stdlib SMTP send (smtplib + email.mime.text) - no new
    dependency added to requirements.txt. Never logs the SMTP password."""
    username = settings.EMAIL_SMTP_USERNAME.strip()
    password = (settings.EMAIL_SMTP_PASSWORD or "").strip()

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = (settings.EMAIL_FROM_ADDRESS or username).strip()
    message["To"] = to_address

    try:
        with smtplib.SMTP(settings.EMAIL_SMTP_HOST.strip(), settings.EMAIL_SMTP_PORT,
                          timeout=settings.EMAIL_SMTP_TIMEOUT_SECONDS) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            refused = server.sendmail(message["From"], [to_address], message.as_string())
        if refused:
            logger.error(f"Inventory alert email refused for {to_address}: {refused}")
            return False
        logger.info(f"Email sent to {to_address}: {subject}")
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error(f"Failed to send email to {to_address}: SMTP authentication rejected for user "
                     f"{_mask(username)} (code {exc.smtp_code}). For Gmail, check that the App "
                     f"Password in OMS360_EMAIL_SMTP_PASSWORD is still valid and 2-Step "
                     f"Verification is on.")
    except smtplib.SMTPRecipientsRefused as exc:
        logger.error(f"Failed to send email to {to_address}: recipient refused "
                     f"({list(exc.recipients.values())}).")
    except smtplib.SMTPSenderRefused as exc:
        logger.error(f"Failed to send email to {to_address}: sender {exc.sender} refused "
                     f"(code {exc.smtp_code}).")
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected) as exc:
        logger.error(f"Failed to send email to {to_address}: SMTP server "
                     f"{settings.EMAIL_SMTP_HOST}:{settings.EMAIL_SMTP_PORT} closed/refused the "
                     f"connection ({type(exc).__name__}).")
    except smtplib.SMTPException as exc:
        logger.error(f"Failed to send email to {to_address}: SMTP error ({type(exc).__name__}: {exc}).")
    except (socket.timeout, OSError) as exc:  # DNS failure, timeout, network unreachable
        logger.error(f"Failed to send email to {to_address}: cannot reach SMTP server "
                     f"{settings.EMAIL_SMTP_HOST}:{settings.EMAIL_SMTP_PORT} "
                     f"({type(exc).__name__}: {exc}).")
    except Exception as exc:  # never let a notification break the caller
        logger.error(f"Failed to send email to {to_address}: {type(exc).__name__}: {exc}")
    return False


def _send_via_brevo(to_address: str, subject: str, body: str) -> bool:
    """Sends one email through Brevo's Transactional Email HTTPS API
    (POST /v3/smtp/email, HTTPS port 443 - works where SMTP ports are
    blocked). Stdlib urllib only, no new dependency. Never raises and never
    logs the API key; Brevo error bodies are logged truncated."""
    api_key = (settings.BREVO_API_KEY or "").strip()
    payload = {
        "sender": {"name": (settings.EMAIL_FROM_NAME or "OMS-360").strip(),
                   "email": settings.EMAIL_FROM_ADDRESS.strip()},
        "to": [{"email": to_address}],
        "subject": subject,
        "textContent": body,
    }
    request = urllib.request.Request(
        settings.BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"api-key": api_key, "content-type": "application/json", "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.EMAIL_SMTP_TIMEOUT_SECONDS) as resp:
            status_code = resp.status
            raw = resp.read().decode("utf-8", errors="replace")
        if 200 <= status_code < 300:
            message_id = ""
            try:
                message_id = json.loads(raw or "{}").get("messageId", "")
            except ValueError:
                pass
            logger.info(f"Email sent via Brevo to {_mask(to_address)}: {subject} (messageId={message_id})")
            return True
        logger.error(f"Brevo API returned HTTP {status_code} for {_mask(to_address)}: {raw[:300]}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        hint = " - check OMS360_BREVO_API_KEY" if exc.code in (401, 403) else ""
        logger.error(f"Failed to send email via Brevo to {_mask(to_address)}: HTTP {exc.code}{hint} "
                     f"({detail}).")
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        logger.error(f"Failed to send email via Brevo to {_mask(to_address)}: cannot reach Brevo API "
                     f"({type(exc).__name__}: {getattr(exc, 'reason', exc)}).")
    except Exception as exc:  # never let a notification break the caller
        logger.error(f"Failed to send email via Brevo to {_mask(to_address)}: {type(exc).__name__}: {exc}")
    return False


def _send(event_type: str, order_id: str, customer_name: str, mobile: str, message: str):
    if not settings.FEATURE_FLAGS.get("notifications_enabled", False):
        logger.info(f"[notifications disabled] Would send '{event_type}' to {mobile}: {message}")
        return False
    logger.info(f"[STUB - not actually sent] '{event_type}' SMS/email queued for {mobile}: {message}")
    return True
