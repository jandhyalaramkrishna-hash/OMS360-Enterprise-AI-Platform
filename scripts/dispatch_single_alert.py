"""
One-off, targeted inventory alert email dispatch (OMS360 ops tool).

Sends the email for exactly ONE inventory_alerts row, using the existing
inventory_service._deliver_alert() - the same code path dispatch-pending
uses - so no new endpoint and no change to application code.

Safety checks (aborts before any SMTP connection if one fails):
  - notifications feature flag must be enabled
  - configured recipient must match EXPECTED_RECIPIENT
  - alert must exist, match EXPECTED_ITEM_ID, and be PENDING or FAILED
Never touches inventory rows. Never prints SMTP credentials.
Prints a before/after snapshot of the protected alerts to prove they
were not changed.

Run (PowerShell, from the project folder):
  Get-Content scripts\\dispatch_single_alert.py -Raw | docker exec -i oms360_core_engine python -
"""
import logging
import sys

TARGET_ALERT_ID = 12
EXPECTED_ITEM_ID = "ITEM-1053"
EXPECTED_RECIPIENT = "jandhyala.ramkrishna@gmail.com"
PROTECTED_ALERT_IDS = (5, 6, 13)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

sys.path.insert(0, "/workspace")
from app.config import settings                      # noqa: E402
from app.database import SessionLocal                # noqa: E402
from app.models import InventoryAlert, Inventory     # noqa: E402
from app.services import inventory_service           # noqa: E402


def snapshot(db, ids):
    rows = db.query(InventoryAlert).filter(InventoryAlert.alert_id.in_(ids)).order_by(InventoryAlert.alert_id).all()
    return {r.alert_id: (r.item_id, r.alert_type, r.notification_status, r.recipient_email,
                         r.remaining_stock, str(r.created_at)) for r in rows}


def abort(msg):
    print(f"ABORTED (no email sent): {msg}")
    sys.exit(1)


def main():
    if not settings.FEATURE_FLAGS.get("notifications_enabled", False):
        abort("OMS360_FEATURE_NOTIFICATIONS is not true in this container.")
    recipient = (settings.INVENTORY_ALERT_EMAIL or "").strip()
    if recipient.lower() != EXPECTED_RECIPIENT.lower():
        abort(f"configured recipient is '{recipient}', expected '{EXPECTED_RECIPIENT}'.")

    db = SessionLocal()
    try:
        protected_before = snapshot(db, PROTECTED_ALERT_IDS)
        alert = db.get(InventoryAlert, TARGET_ALERT_ID)
        if alert is None:
            abort(f"alert {TARGET_ALERT_ID} not found.")
        if alert.item_id != EXPECTED_ITEM_ID:
            abort(f"alert {TARGET_ALERT_ID} is for {alert.item_id}, expected {EXPECTED_ITEM_ID}.")
        if alert.notification_status not in ("PENDING", "FAILED"):
            abort(f"alert {TARGET_ALERT_ID} status is {alert.notification_status} (only PENDING/FAILED are sent).")

        stock = db.get(Inventory, alert.item_id)
        stock_before = (stock.remaining_stock, stock.status) if stock else None

        print(f"BEFORE alert {TARGET_ALERT_ID}: item={alert.item_id} type={alert.alert_type} "
              f"status={alert.notification_status} recipient={alert.recipient_email}")
        result = inventory_service._deliver_alert(db, alert, respect_cooldown=False)

        db.expire_all()
        alert = db.get(InventoryAlert, TARGET_ALERT_ID)
        protected_after = snapshot(db, PROTECTED_ALERT_IDS)
        stock = db.get(Inventory, alert.item_id)
        stock_after = (stock.remaining_stock, stock.status) if stock else None

        print(f"SMTP RESULT: {result}")
        print(f"AFTER  alert {TARGET_ALERT_ID}: status={alert.notification_status} recipient={alert.recipient_email}")
        print(f"INVENTORY {alert.item_id} unchanged: {stock_before == stock_after} {stock_after}")
        for aid in PROTECTED_ALERT_IDS:
            b, a = protected_before.get(aid), protected_after.get(aid)
            print(f"PROTECTED alert {aid}: unchanged={b == a} status={a[2] if a else None}")
        ok = (result == "SENT" and alert.notification_status == "SENT"
              and protected_before == protected_after and stock_before == stock_after)
        print("RESULT: PASS - exactly one alert email sent" if ok else "RESULT: CHECK OUTPUT ABOVE")
        sys.exit(0 if ok else 2)
    finally:
        db.close()


main()
