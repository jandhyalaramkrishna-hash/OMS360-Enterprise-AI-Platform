"""
Low-stock / out-of-stock email notification tests (2026-11-20 fix).

Self-contained: no live MySQL and no real SMTP server are needed.
  - Database: in-memory SQLite built from the same app.database.Base
    metadata (same approach as tests/ai/conftest.py), with autoflush=False
    to match app.database.SessionLocal.
  - SMTP: smtplib.SMTP is replaced with a fake inside notification_service,
    so success, authentication failure, connection failure and recipient
    refusal are all exercised deterministically and no email is ever sent.

Run:  pytest tests/test_inventory_notifications.py -v
"""

import logging
import smtplib
import socket

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.config import settings
from app.core.exceptions import InventoryLockException
from app.database import Base
from app.services import inventory_service, notification_service

TEST_PASSWORD = "abcdwxyzsecretpw"   # fake app password - must never appear in logs
TEST_USER = "ops.sender@example.com"
TEST_RECIPIENT = "admin.alerts@example.com"
THRESHOLD = 5                       # inventory_service.DEFAULT_LOW_STOCK_THRESHOLD (LOW_STOCK when remaining < 5)


# --------------------------------------------------------------------------
# Fake SMTP
# --------------------------------------------------------------------------
class FakeSMTP:
    """Records every SMTP interaction. Behaviour is driven by class attrs."""
    instances = []
    fail_connect = None      # exception raised from __init__
    fail_login = None        # exception raised from login()
    fail_sendmail = None     # exception raised from sendmail()
    refused = {}             # value returned from sendmail()

    def __init__(self, host, port, timeout=None):
        if FakeSMTP.fail_connect:
            raise FakeSMTP.fail_connect
        self.host, self.port, self.timeout = host, port, timeout
        self.calls, self.sent = [], []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.calls.append("quit")
        return False

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append("login")
        self.login_args = (user, password)
        if FakeSMTP.fail_login:
            raise FakeSMTP.fail_login

    def sendmail(self, from_addr, to_addrs, msg):
        self.calls.append("sendmail")
        if FakeSMTP.fail_sendmail:
            raise FakeSMTP.fail_sendmail
        self.sent.append((from_addr, list(to_addrs), msg))
        return FakeSMTP.refused

    @classmethod
    def all_sent(cls):
        return [m for inst in cls.instances for m in inst.sent]

    @classmethod
    def reset(cls):
        cls.instances = []
        cls.fail_connect = cls.fail_login = cls.fail_sendmail = None
        cls.refused = {}


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def smtp_env(monkeypatch):
    FakeSMTP.reset()
    monkeypatch.setattr(notification_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", True)
    monkeypatch.setattr(settings, "EMAIL_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "EMAIL_SMTP_PORT", 587)
    monkeypatch.setattr(settings, "EMAIL_SMTP_USERNAME", TEST_USER)
    # trailing CR/space simulates a CRLF .env - must be trimmed before login
    monkeypatch.setattr(settings, "EMAIL_SMTP_PASSWORD", TEST_PASSWORD + "\r ")
    monkeypatch.setattr(settings, "EMAIL_FROM_ADDRESS", TEST_USER)
    monkeypatch.setattr(settings, "INVENTORY_ALERT_EMAIL", TEST_RECIPIENT)
    monkeypatch.setattr(settings, "NOTIFICATION_RETRY_COOLDOWN_SECONDS", 300)
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "smtp")   # local default transport
    inventory_service._last_failed_attempt.clear()
    yield
    FakeSMTP.reset()
    inventory_service._last_failed_attempt.clear()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def captured_logs():
    """Collects every record logged by the two services under test."""
    records = []

    class _Collector(logging.Handler):
        def emit(self, record):
            records.append(self.format(record))

    handler = _Collector(level=logging.DEBUG)
    loggers = [logging.getLogger("oms360.services.notification_service"),
               logging.getLogger("oms360.services.inventory_service")]
    old_levels = [lg.level for lg in loggers]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
    yield records
    for lg, lvl in zip(loggers, old_levels):
        lg.removeHandler(handler)
        lg.setLevel(lvl)


def _add_item(db, item_id="ITEM-T1", stock=7, status="ACTIVE", name="Paneer Tikka"):
    row = models.Inventory(item_id=item_id, item_name=name, price=100, total_stock=stock,
                           remaining_stock=stock, used_stock=0, status=status)
    db.add(row)
    db.commit()
    return row


def _reserve(db, item_id, qty, order_id="ORD-1"):
    """Mirrors order_service: lock, reserve, commit, then dispatch."""
    row = inventory_service.lock_and_fetch(db, [item_id])[item_id]
    inventory_service.reserve_stock(db, item_id, row, qty, order_id)
    db.commit()
    return inventory_service.dispatch_pending_notifications(db)


def _alerts(db, item_id="ITEM-T1"):
    return (db.query(models.InventoryAlert).filter(models.InventoryAlert.item_id == item_id)
            .order_by(models.InventoryAlert.alert_id).all())


# --------------------------------------------------------------------------
# notification_service unit tests
# --------------------------------------------------------------------------
def test_successful_delivery_returns_sent_and_uses_tls_login(captured_logs):
    status = notification_service.send_low_stock_alert("ITEM-T1", "Paneer Tikka", 4, TEST_RECIPIENT,
                                                       alert_type="LOW_STOCK", threshold=THRESHOLD)
    assert status == notification_service.STATUS_SENT
    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.gmail.com", 587)
    assert smtp.calls.index("starttls") < smtp.calls.index("login") < smtp.calls.index("sendmail")
    assert smtp.login_args == (TEST_USER, TEST_PASSWORD)          # CR/space trimmed
    from_addr, to_addrs, msg = smtp.sent[0]
    assert from_addr == TEST_USER and to_addrs == [TEST_RECIPIENT]
    assert "Remaining stock: 4" in msg and "LOW_STOCK" in msg
    assert all(TEST_PASSWORD not in line for line in captured_logs)


def test_out_of_stock_email_has_distinct_subject():
    subject, body = notification_service._build_alert_message("ITEM-T1", "Paneer Tikka", 0,
                                                              "OUT_OF_STOCK", 10)
    assert "OUT OF STOCK" in subject
    assert "out of stock" in body and "Alert type: OUT_OF_STOCK" in body
    assert notification_service.send_low_stock_alert(
        "ITEM-T1", "Paneer Tikka", 0, TEST_RECIPIENT, alert_type="OUT_OF_STOCK") == "SENT"


def test_feature_flag_off_returns_pending_and_never_connects(monkeypatch):
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", False)
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "PENDING"
    assert FakeSMTP.instances == []


@pytest.mark.parametrize("setting", ["EMAIL_SMTP_HOST", "EMAIL_SMTP_USERNAME", "EMAIL_SMTP_PASSWORD"])
def test_incomplete_smtp_config_returns_failed_without_connecting(monkeypatch, setting, captured_logs):
    monkeypatch.setattr(settings, setting, "")
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"
    assert FakeSMTP.instances == []
    assert any("configuration incomplete" in line for line in captured_logs)


def test_missing_recipient_returns_failed():
    assert notification_service.send_low_stock_alert("I", "N", 1, "") == "FAILED"
    assert FakeSMTP.instances == []


def test_auth_failure_returns_failed_and_never_logs_password(captured_logs):
    FakeSMTP.fail_login = smtplib.SMTPAuthenticationError(
        535, b"5.7.8 Username and Password not accepted")
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"
    joined = "\n".join(captured_logs)
    assert "authentication rejected" in joined and "535" in joined
    assert TEST_PASSWORD not in joined
    assert TEST_USER not in joined           # username is masked
    assert "op***@example.com" in joined


@pytest.mark.parametrize("exc", [
    socket.gaierror(-3, "Temporary failure in name resolution"),
    socket.timeout("timed out"),
    ConnectionRefusedError(111, "Connection refused"),
    smtplib.SMTPConnectError(421, b"Service not available"),
])
def test_connection_failures_return_failed(exc, captured_logs):
    FakeSMTP.fail_connect = exc
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"
    assert any("smtp.gmail.com:587" in line for line in captured_logs)


def test_recipient_refused_returns_failed():
    FakeSMTP.fail_sendmail = smtplib.SMTPRecipientsRefused({TEST_RECIPIENT: (550, b"no such user")})
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"


def test_partial_refusal_from_sendmail_returns_failed():
    FakeSMTP.refused = {TEST_RECIPIENT: (550, b"rejected")}
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"


def test_notify_low_stock_keeps_backward_compatible_bool():
    assert notification_service.notify_low_stock("I", "N", 1, recipient_email=TEST_RECIPIENT) is True
    FakeSMTP.fail_login = smtplib.SMTPAuthenticationError(535, b"bad")
    assert notification_service.notify_low_stock("I", "N", 1, recipient_email=TEST_RECIPIENT) is False


# --------------------------------------------------------------------------
# inventory_service integration (SQLite + fake SMTP)
# --------------------------------------------------------------------------
def test_crossing_threshold_creates_one_alert_and_sends_email(db):
    _add_item(db, stock=7)
    summary = _reserve(db, "ITEM-T1", 3)                       # 7 -> 4 (< 5)
    alerts = _alerts(db)
    assert len(alerts) == 1
    a = alerts[0]
    assert (a.alert_type, a.notification_status, a.recipient_email) == ("LOW_STOCK", "SENT", TEST_RECIPIENT)
    assert (a.remaining_stock, a.threshold_value) == (4, THRESHOLD)
    assert summary["sent"] == 1 and len(FakeSMTP.all_sent()) == 1
    assert FakeSMTP.all_sent()[0][1] == [TEST_RECIPIENT]
    assert db.get(models.Inventory, "ITEM-T1").status == "LOW_STOCK"


def test_email_is_not_sent_before_the_transaction_commits(db):
    _add_item(db, stock=7)
    row = inventory_service.lock_and_fetch(db, ["ITEM-T1"])["ITEM-T1"]
    inventory_service.reserve_stock(db, "ITEM-T1", row, 3, "ORD-1")
    assert FakeSMTP.instances == []                            # nothing sent mid-transaction
    db.commit()
    inventory_service.dispatch_pending_notifications(db)
    assert len(FakeSMTP.all_sent()) == 1


def test_rolled_back_transaction_sends_no_email(db):
    _add_item(db, stock=7)
    _add_item(db, item_id="ITEM-T2", stock=1, name="Lassi")
    rows = inventory_service.lock_and_fetch(db, ["ITEM-T1", "ITEM-T2"])
    inventory_service.reserve_stock(db, "ITEM-T1", rows["ITEM-T1"], 3, "ORD-9")  # raises alert
    with pytest.raises(InventoryLockException):
        inventory_service.reserve_stock(db, "ITEM-T2", rows["ITEM-T2"], 5, "ORD-9")
    db.rollback()                                              # what order_service does on failure
    summary = inventory_service.dispatch_pending_notifications(db)
    assert summary["attempted"] == 0 and FakeSMTP.instances == []
    assert _alerts(db) == []


def test_repeated_low_stock_processing_does_not_duplicate_alerts_or_emails(db):
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 3, "ORD-1")                        # 4  -> alert + email
    _reserve(db, "ITEM-T1", 1, "ORD-2")                        # 3
    _reserve(db, "ITEM-T1", 2, "ORD-3")                        # 1
    assert len(_alerts(db)) == 1
    assert len(FakeSMTP.all_sent()) == 1


def test_same_item_twice_in_one_transaction_creates_single_alert(db):
    _add_item(db, stock=7)
    row = inventory_service.lock_and_fetch(db, ["ITEM-T1"])["ITEM-T1"]
    inventory_service.reserve_stock(db, "ITEM-T1", row, 3, "ORD-1")
    inventory_service.reserve_stock(db, "ITEM-T1", row, 1, "ORD-1")
    db.commit()
    inventory_service.dispatch_pending_notifications(db)
    assert len(_alerts(db)) == 1 and len(FakeSMTP.all_sent()) == 1


def test_low_to_out_of_stock_sends_out_of_stock_notification(db):
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 3)                                 # LOW_STOCK
    _reserve(db, "ITEM-T1", 4)                                 # 0 -> OUT_OF_STOCK
    alerts = _alerts(db)
    assert [a.alert_type for a in alerts] == ["LOW_STOCK", "OUT_OF_STOCK"]
    assert all(a.notification_status == "SENT" for a in alerts)
    assert len(FakeSMTP.all_sent()) == 2
    assert "OUT OF STOCK" in FakeSMTP.all_sent()[1][2] or "OUT_OF_STOCK" in FakeSMTP.all_sent()[1][2]
    assert db.get(models.Inventory, "ITEM-T1").status == "OUT_OF_STOCK"


def test_direct_active_to_out_of_stock_sends_one_email(db):
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 7)
    assert [a.alert_type for a in _alerts(db)] == ["OUT_OF_STOCK"]
    assert len(FakeSMTP.all_sent()) == 1


def test_smtp_failure_marks_failed_then_retries_after_cooldown_without_new_row(db, monkeypatch):
    _add_item(db, stock=7)
    FakeSMTP.fail_login = smtplib.SMTPAuthenticationError(535, b"bad credentials")
    _reserve(db, "ITEM-T1", 3, "ORD-1")
    assert _alerts(db)[0].notification_status == "FAILED"
    attempts_after_failure = len(FakeSMTP.instances)

    # Within cooldown: the next order must not hit SMTP again.
    _reserve(db, "ITEM-T1", 1, "ORD-2")
    assert len(FakeSMTP.instances) == attempts_after_failure
    assert _alerts(db)[0].notification_status == "FAILED"

    # SMTP fixed and cooldown elapsed: same alert row is retried and SENT.
    FakeSMTP.fail_login = None
    monkeypatch.setattr(settings, "NOTIFICATION_RETRY_COOLDOWN_SECONDS", 0)
    _reserve(db, "ITEM-T1", 1, "ORD-3")
    alerts = _alerts(db)
    assert len(alerts) == 1 and alerts[0].notification_status == "SENT"
    assert len(FakeSMTP.all_sent()) == 1

    # Once SENT, further processing sends nothing more.
    _reserve(db, "ITEM-T1", 1, "ORD-4")
    assert len(FakeSMTP.all_sent()) == 1


def test_notifications_disabled_leaves_pending_and_dispatch_delivers_later(db, monkeypatch):
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", False)
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 3)
    assert _alerts(db)[0].notification_status == "PENDING"
    assert FakeSMTP.instances == []

    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", True)
    summary = inventory_service.dispatch_open_alerts(db)
    assert summary["sent"] == 1
    assert _alerts(db)[0].notification_status == "SENT"
    # Second run: nothing left to send, no duplicate.
    assert inventory_service.dispatch_open_alerts(db)["attempted"] == 0
    assert len(FakeSMTP.all_sent()) == 1


def test_dispatch_open_alerts_resends_existing_failed_records_without_touching_inventory(db):
    # Pre-existing data as it looks in the live DB today: item already
    # LOW_STOCK, its alert stuck at FAILED.
    _add_item(db, stock=4, status="LOW_STOCK")
    db.add(models.InventoryAlert(item_id="ITEM-T1", item_name="Paneer Tikka", remaining_stock=4,
                                 threshold_value=THRESHOLD, alert_type="LOW_STOCK", notification_type="EMAIL",
                                 notification_status="FAILED", recipient_email=TEST_RECIPIENT))
    # Stale alert for an item that has since been restocked - must be ignored.
    _add_item(db, item_id="ITEM-T2", stock=80, name="Lassi")
    db.add(models.InventoryAlert(item_id="ITEM-T2", item_name="Lassi", remaining_stock=2,
                                 threshold_value=THRESHOLD, alert_type="LOW_STOCK", notification_type="EMAIL",
                                 notification_status="FAILED", recipient_email=TEST_RECIPIENT))
    db.commit()
    before = [(r.item_id, r.remaining_stock, r.total_stock, r.used_stock, r.status)
              for r in db.query(models.Inventory).order_by(models.Inventory.item_id)]

    summary = inventory_service.dispatch_open_alerts(db)

    assert summary["sent"] == 1 and summary["alerts"][0]["item_id"] == "ITEM-T1"
    assert _alerts(db, "ITEM-T1")[0].notification_status == "SENT"
    assert _alerts(db, "ITEM-T2")[0].notification_status == "FAILED"   # stale, untouched
    assert db.query(models.InventoryAlert).count() == 2                 # no rows created
    after = [(r.item_id, r.remaining_stock, r.total_stock, r.used_stock, r.status)
             for r in db.query(models.Inventory).order_by(models.Inventory.item_id)]
    assert before == after


def test_existing_low_stock_item_without_alert_gets_alert_on_next_reservation(db):
    _add_item(db, stock=4, status="LOW_STOCK")                 # e.g. seeded/manual status
    _reserve(db, "ITEM-T1", 1)                                 # 3
    assert len(_alerts(db)) == 1 and len(FakeSMTP.all_sent()) == 1


def test_recipient_comes_from_current_configuration(db, monkeypatch):
    monkeypatch.setattr(settings, "INVENTORY_ALERT_EMAIL", "")
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", True)
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 3)
    assert _alerts(db)[0].notification_status == "FAILED"      # no recipient -> not sent

    monkeypatch.setattr(settings, "INVENTORY_ALERT_EMAIL", "new.admin@example.com")
    inventory_service.dispatch_open_alerts(db)
    a = _alerts(db)[0]
    assert a.notification_status == "SENT" and a.recipient_email == "new.admin@example.com"
    assert FakeSMTP.all_sent()[0][1] == ["new.admin@example.com"]


def test_update_item_stock_correction_emails_once_and_restock_starts_new_episode(db):
    _add_item(db, stock=50)
    inventory_service.update_item(db, "ITEM-T1", stock=3)       # -> LOW_STOCK, email
    inventory_service.update_item(db, "ITEM-T1", stock=3)       # unchanged -> nothing
    inventory_service.update_item(db, "ITEM-T1", price=120)     # no stock -> nothing
    assert len(_alerts(db)) == 1 and len(FakeSMTP.all_sent()) == 1

    inventory_service.restock(db, "ITEM-T1", 40)                # 43 > threshold -> ACTIVE
    assert db.get(models.Inventory, "ITEM-T1").status == "ACTIVE"

    _reserve(db, "ITEM-T1", 40)                                 # 3 -> new LOW_STOCK episode
    assert [a.alert_type for a in _alerts(db)] == ["LOW_STOCK", "LOW_STOCK"]
    assert len(FakeSMTP.all_sent()) == 2


def test_update_item_recover_to_active_still_works(db):
    _add_item(db, stock=3, status="LOW_STOCK")
    row = inventory_service.update_item(db, "ITEM-T1", stock=500)
    assert row.status == "ACTIVE" and FakeSMTP.instances == []


def test_restock_partial_from_low_stays_low(db):
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 4)                                  # 3, LOW_STOCK
    inventory_service.restock(db, "ITEM-T1", 1)                 # 4, still < 5
    assert db.get(models.Inventory, "ITEM-T1").status == "LOW_STOCK"
    _reserve(db, "ITEM-T1", 1)
    assert len(FakeSMTP.all_sent()) == 1                        # still same episode


def test_release_stock_above_threshold_recovers_status(db):
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 5)                                  # 2, LOW_STOCK
    row = inventory_service.lock_and_fetch(db, ["ITEM-T1"])["ITEM-T1"]
    inventory_service.release_stock(db, "ITEM-T1", row, 5, "ORD-1", "Cancelled")
    db.commit()
    assert db.get(models.Inventory, "ITEM-T1").status == "ACTIVE"


def test_no_password_in_logs_across_full_failure_flow(db, captured_logs):
    _add_item(db, stock=7)
    FakeSMTP.fail_login = smtplib.SMTPAuthenticationError(535, b"5.7.8 not accepted")
    _reserve(db, "ITEM-T1", 3)
    FakeSMTP.fail_login = None
    FakeSMTP.fail_connect = OSError("network unreachable")
    inventory_service.dispatch_open_alerts(db)
    assert captured_logs, "expected failure logs"
    assert all(TEST_PASSWORD not in line for line in captured_logs)


# --------------------------------------------------------------------------
# Route: POST /api/v1/inventory/alerts/dispatch-pending
# --------------------------------------------------------------------------
def test_dispatch_pending_route(db, monkeypatch):
    from app.database import get_db
    from app.routes import inventory as inventory_routes

    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", False)
    _add_item(db, stock=7)
    _reserve(db, "ITEM-T1", 3)
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", True)

    app = FastAPI()
    app.include_router(inventory_routes.router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    resp = client.post("/api/v1/inventory/alerts/dispatch-pending")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sent"] == 1 and body["alerts"][0]["notification_status"] == "SENT"
    assert client.post("/api/v1/inventory/alerts/dispatch-pending").json()["attempted"] == 0


# --------------------------------------------------------------------------
# create_item(): new item created already at / below the threshold
# (DEF-007, 2026-11-21 - "Millet Idly created with stock 2 stayed ACTIVE,
# no alert, no email")
# --------------------------------------------------------------------------
def _created_alerts(db, item_id):
    return _alerts(db, item_id)


def test_create_item_below_threshold_is_low_stock_with_one_alert_and_email(db):
    row = inventory_service.create_item(db, item_name="Millet Idly", price=150, total_stock=2,
                                        status="ACTIVE")   # dialog always sends ACTIVE
    assert row.status == "LOW_STOCK"
    assert db.get(models.Item, row.item_id).status == "LOW_STOCK"     # items mirrored
    alerts = _created_alerts(db, row.item_id)
    assert len(alerts) == 1
    a = alerts[0]
    assert (a.item_id, a.item_name, a.alert_type) == (row.item_id, "Millet Idly", "LOW_STOCK")
    assert (a.remaining_stock, a.threshold_value) == (2, THRESHOLD)
    assert (a.notification_status, a.recipient_email) == ("SENT", TEST_RECIPIENT)
    assert len(FakeSMTP.all_sent()) == 1


def test_create_item_exactly_at_five_stays_active_without_alert(db):
    row = inventory_service.create_item(db, item_name="Ragi Malt", price=60, total_stock=5)
    assert row.status == "ACTIVE"
    assert _created_alerts(db, row.item_id) == []


def test_create_item_above_threshold_stays_active_without_alert(db):
    row = inventory_service.create_item(db, item_name="Millet Dosa", price=120, total_stock=25,
                                        status="ACTIVE")
    assert row.status == "ACTIVE"
    assert _created_alerts(db, row.item_id) == []
    assert FakeSMTP.instances == []


def test_create_item_with_zero_stock_is_out_of_stock_with_one_alert(db):
    row = inventory_service.create_item(db, item_name="Jowar Roti", price=40, total_stock=0)
    assert row.status == "OUT_OF_STOCK"
    alerts = _created_alerts(db, row.item_id)
    assert [a.alert_type for a in alerts] == ["OUT_OF_STOCK"]
    assert len(FakeSMTP.all_sent()) == 1


def test_create_item_explicit_inactive_is_kept_and_raises_no_alert(db):
    row = inventory_service.create_item(db, item_name="Seasonal Item", price=80, total_stock=2,
                                        status="INACTIVE")
    assert row.status == "INACTIVE"
    assert _created_alerts(db, row.item_id) == []
    assert FakeSMTP.instances == []


def test_create_item_low_then_orders_do_not_send_duplicate_emails(db):
    row = inventory_service.create_item(db, item_name="Millet Idly", price=150, total_stock=4)
    _reserve(db, row.item_id, 1, "ORD-A")       # 3 - same LOW_STOCK episode
    _reserve(db, row.item_id, 1, "ORD-B")       # 2
    assert len(_created_alerts(db, row.item_id)) == 1
    assert len(FakeSMTP.all_sent()) == 1


def test_create_item_with_notifications_disabled_records_pending_alert(db, monkeypatch):
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", False)
    row = inventory_service.create_item(db, item_name="Millet Idly", price=150, total_stock=2)
    alerts = _created_alerts(db, row.item_id)
    assert row.status == "LOW_STOCK"
    assert [a.notification_status for a in alerts] == ["PENDING"]
    assert FakeSMTP.instances == []


def test_create_item_does_not_touch_existing_inventory_rows(db):
    _add_item(db, item_id="ITEM-T1", stock=3, status="ACTIVE")   # pre-existing low row, no alert
    inventory_service.create_item(db, item_name="Millet Idly", price=150, total_stock=2)
    existing = db.get(models.Inventory, "ITEM-T1")
    assert (existing.status, existing.remaining_stock) == ("ACTIVE", 3)
    assert _alerts(db, "ITEM-T1") == []


# --------------------------------------------------------------------------
# Business rule boundaries (2026-11-21): remaining_stock 0 -> OUT_OF_STOCK +
# email, 1-4 -> LOW_STOCK + email, 5 and above -> ACTIVE, no email. Applied
# identically to item creation, manual stock updates and order reservations.
# --------------------------------------------------------------------------
BOUNDARIES = [
    (0, "OUT_OF_STOCK", ["OUT_OF_STOCK"]),
    (1, "LOW_STOCK", ["LOW_STOCK"]),
    (4, "LOW_STOCK", ["LOW_STOCK"]),
    (5, "ACTIVE", []),
    (6, "ACTIVE", []),
]


@pytest.mark.parametrize("stock,expected_status,expected_alerts", BOUNDARIES)
def test_boundary_on_item_creation(db, stock, expected_status, expected_alerts):
    row = inventory_service.create_item(db, item_name="Boundary Item", price=10, total_stock=stock,
                                        status="ACTIVE")
    assert row.status == expected_status
    assert [a.alert_type for a in _alerts(db, row.item_id)] == expected_alerts
    assert len(FakeSMTP.all_sent()) == len(expected_alerts)


@pytest.mark.parametrize("stock,expected_status,expected_alerts", BOUNDARIES)
def test_boundary_on_manual_stock_update(db, stock, expected_status, expected_alerts):
    _add_item(db, stock=50)
    row = inventory_service.update_item(db, "ITEM-T1", stock=stock)
    assert row.status == expected_status
    assert [a.alert_type for a in _alerts(db)] == expected_alerts
    assert len(FakeSMTP.all_sent()) == len(expected_alerts)


@pytest.mark.parametrize("stock,expected_status,expected_alerts", BOUNDARIES)
def test_boundary_on_order_reservation(db, stock, expected_status, expected_alerts):
    _add_item(db, stock=20)
    _reserve(db, "ITEM-T1", 20 - stock)
    row = db.get(models.Inventory, "ITEM-T1")
    assert row.remaining_stock == stock
    assert row.status == expected_status
    assert [a.alert_type for a in _alerts(db)] == expected_alerts
    assert len(FakeSMTP.all_sent()) == len(expected_alerts)


def test_rule_uses_remaining_stock_not_total_stock(db):
    # total_stock is large, remaining_stock is low -> must alert.
    row = models.Inventory(item_id="ITEM-T9", item_name="Big Batch", price=10, total_stock=500,
                           remaining_stock=6, used_stock=494, status="ACTIVE")
    db.add(row)
    db.commit()
    _reserve(db, "ITEM-T9", 2)                                   # remaining 4
    r = db.get(models.Inventory, "ITEM-T9")
    assert (r.total_stock, r.remaining_stock, r.status) == (500, 4, "LOW_STOCK")
    assert [a.alert_type for a in _alerts(db, "ITEM-T9")] == ["LOW_STOCK"]


# --------------------------------------------------------------------------
# Brevo HTTPS Transactional Email API (production transport, 2026-11-21).
# urllib.request.urlopen is faked - no network call, no real email.
# --------------------------------------------------------------------------
import io
import json
import urllib.error

TEST_BREVO_KEY = "xkeysib-TESTONLY-0000000000000000"   # fake key - must never appear in logs
TEST_BREVO_SENDER = "alerts@zelqa.in"


class FakeBrevo:
    calls = []
    status = 201
    body = b'{"messageId":"<test-msg-1@smtp-relay.mailin.fr>"}'
    error = None            # exception raised from urlopen

    class _Resp:
        def __init__(self, status, body):
            self.status, self._body = status, body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    @classmethod
    def urlopen(cls, request, timeout=None):
        cls.calls.append({"url": request.full_url, "method": request.get_method(),
                          "headers": {k.lower(): v for k, v in request.header_items()},
                          "json": json.loads(request.data.decode()), "timeout": timeout})
        if cls.error:
            raise cls.error
        return cls._Resp(cls.status, cls.body)

    @classmethod
    def reset(cls):
        cls.calls, cls.status, cls.error = [], 201, None
        cls.body = b'{"messageId":"<test-msg-1@smtp-relay.mailin.fr>"}'


@pytest.fixture()
def brevo_env(monkeypatch):
    FakeBrevo.reset()
    monkeypatch.setattr(notification_service.urllib.request, "urlopen", FakeBrevo.urlopen)
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "brevo")
    monkeypatch.setattr(settings, "BREVO_API_KEY", TEST_BREVO_KEY + "\r ")
    monkeypatch.setattr(settings, "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
    monkeypatch.setattr(settings, "EMAIL_FROM_ADDRESS", TEST_BREVO_SENDER)
    monkeypatch.setattr(settings, "EMAIL_FROM_NAME", "OMS-360 Inventory Alerts")
    yield FakeBrevo
    FakeBrevo.reset()


def _http_error(code, body=b'{"code":"unauthorized","message":"Key not found"}'):
    return urllib.error.HTTPError("https://api.brevo.com/v3/smtp/email", code, "err", {}, io.BytesIO(body))


def test_brevo_success_returns_sent_with_correct_request(brevo_env, captured_logs):
    status = notification_service.send_low_stock_alert("ITEM-1002", "Millet Idly", 2, TEST_RECIPIENT,
                                                       alert_type="LOW_STOCK", threshold=THRESHOLD)
    assert status == "SENT"
    assert FakeSMTP.instances == []                      # SMTP not used in brevo mode
    call = brevo_env.calls[0]
    assert (call["url"], call["method"]) == ("https://api.brevo.com/v3/smtp/email", "POST")
    assert call["headers"]["api-key"] == TEST_BREVO_KEY  # trimmed
    assert call["json"]["sender"]["email"] == TEST_BREVO_SENDER
    assert call["json"]["to"] == [{"email": TEST_RECIPIENT}]
    assert "Millet Idly" in call["json"]["subject"] and "2" in call["json"]["textContent"]
    assert all(TEST_BREVO_KEY not in line for line in captured_logs)


def test_brevo_out_of_stock_uses_out_of_stock_subject(brevo_env):
    notification_service.send_low_stock_alert("ITEM-X", "Jowar Roti", 0, TEST_RECIPIENT,
                                              alert_type="OUT_OF_STOCK", threshold=THRESHOLD)
    assert "OUT OF STOCK" in brevo_env.calls[0]["json"]["subject"]


@pytest.mark.parametrize("code", [400, 401, 403, 429, 500])
def test_brevo_http_errors_return_failed_and_never_log_key(brevo_env, captured_logs, code):
    brevo_env.error = _http_error(code)
    status = notification_service.send_low_stock_alert("ITEM-1002", "Millet Idly", 2, TEST_RECIPIENT)
    assert status == "FAILED"
    assert any(f"HTTP {code}" in line for line in captured_logs)
    assert all(TEST_BREVO_KEY not in line for line in captured_logs)


def test_brevo_network_failure_returns_failed(brevo_env, captured_logs):
    brevo_env.error = urllib.error.URLError("timed out")
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"
    assert any("cannot reach Brevo API" in line for line in captured_logs)


@pytest.mark.parametrize("setting", ["BREVO_API_KEY", "EMAIL_FROM_ADDRESS"])
def test_brevo_incomplete_config_returns_failed_without_calling_api(brevo_env, monkeypatch, setting,
                                                                     captured_logs):
    monkeypatch.setattr(settings, setting, "")
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"
    assert brevo_env.calls == []
    assert any("BREVO configuration incomplete" in line for line in captured_logs)


def test_brevo_notifications_disabled_returns_pending_without_calling_api(brevo_env, monkeypatch):
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", False)
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "PENDING"
    assert brevo_env.calls == []


def test_unknown_provider_returns_failed(monkeypatch, captured_logs):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "carrier-pigeon")
    assert notification_service.send_low_stock_alert("I", "N", 1, TEST_RECIPIENT) == "FAILED"
    assert FakeSMTP.instances == []


def test_brevo_end_to_end_create_low_item_sends_once_and_records_sent(db, brevo_env):
    row = inventory_service.create_item(db, item_name="Millet Idly", price=150, total_stock=2)
    _reserve(db, row.item_id, 1, "ORD-A")                     # same episode - no second email
    alerts = _alerts(db, row.item_id)
    assert [(a.alert_type, a.notification_status) for a in alerts] == [("LOW_STOCK", "SENT")]
    assert len(brevo_env.calls) == 1


def test_brevo_failure_then_dispatch_retries_same_row_without_duplicates(db, brevo_env):
    brevo_env.error = _http_error(401)
    row = inventory_service.create_item(db, item_name="Millet Idly", price=150, total_stock=2)
    assert _alerts(db, row.item_id)[0].notification_status == "FAILED"

    brevo_env.error = None                                     # key fixed
    summary = inventory_service.dispatch_open_alerts(db)
    alerts = _alerts(db, row.item_id)
    assert summary["sent"] == 1 and len(alerts) == 1 and alerts[0].notification_status == "SENT"
    assert inventory_service.dispatch_open_alerts(db)["attempted"] == 0   # nothing re-sent
    assert len(brevo_env.calls) == 2                                      # 1 failed + 1 sent


# --------------------------------------------------------------------------
# 2026-11-21: every alert email lists ALL items currently below 5
# (trigger unchanged - one email per new low/out-of-stock episode)
# --------------------------------------------------------------------------
import email as _email


def _smtp_body(index=0):
    raw = FakeSMTP.all_sent()[index][2]
    return _email.message_from_string(raw).get_payload(decode=True).decode("utf-8")


def test_alert_email_lists_every_item_below_five_lowest_first(db):
    _add_item(db, "ITEM-A", stock=3, status="LOW_STOCK", name="Millet Idly")
    _add_item(db, "ITEM-B", stock=0, status="OUT_OF_STOCK", name="Jowar Roti")
    _add_item(db, "ITEM-C", stock=5, name="Ragi Malt")                 # exactly 5 - not low
    _add_item(db, "ITEM-D", stock=40, name="Millet Dosa")              # healthy
    _add_item(db, "ITEM-E", stock=1, status="INACTIVE", name="Seasonal Item")  # inactive - excluded

    row = inventory_service.create_item(db, item_name="Veg Idly", price=90, total_stock=2)

    assert len(FakeSMTP.all_sent()) == 1                    # still exactly one email
    body = _smtp_body()
    assert "All items currently below 5 (3):" in body
    lines = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("- ")]
    assert lines == [
        "- Jowar Roti (ITEM-B): 0 remaining - OUT OF STOCK",
        f"- Veg Idly ({row.item_id}): 2 remaining - LOW STOCK",
        "- Millet Idly (ITEM-A): 3 remaining - LOW STOCK",
    ]
    assert "Ragi Malt" not in body and "Millet Dosa" not in body and "Seasonal Item" not in body


def test_list_does_not_create_alerts_or_emails_for_other_low_items(db):
    _add_item(db, "ITEM-A", stock=3, status="LOW_STOCK", name="Millet Idly")   # no alert row
    inventory_service.create_item(db, item_name="Veg Idly", price=90, total_stock=2)
    assert len(FakeSMTP.all_sent()) == 1
    assert _alerts(db, "ITEM-A") == []                     # listed, but no alert row created
    assert db.get(models.Inventory, "ITEM-A").remaining_stock == 3   # inventory untouched


def test_already_low_item_update_still_sends_no_duplicate_email(db):
    inventory_service.create_item(db, item_name="Veg Idly", price=90, total_stock=2)
    _add_item(db, "ITEM-A", stock=3, status="LOW_STOCK", name="Millet Idly")
    vi = db.query(models.Inventory).filter(models.Inventory.item_name == "Veg Idly").one()
    _reserve(db, vi.item_id, 1, "ORD-X")                    # same LOW_STOCK episode
    assert len(FakeSMTP.all_sent()) == 1


def test_brevo_email_body_contains_the_full_list(db, brevo_env):
    _add_item(db, "ITEM-A", stock=3, status="LOW_STOCK", name="Millet Idly")
    inventory_service.create_item(db, item_name="Veg Idly", price=90, total_stock=2)
    assert len(brevo_env.calls) == 1
    text = brevo_env.calls[0]["json"]["textContent"]
    assert "All items currently below 5 (2):" in text
    assert "Millet Idly (ITEM-A): 3 remaining - LOW STOCK" in text
    assert "Veg Idly" in text


def test_message_without_list_is_unchanged():
    _, body_without = notification_service._build_alert_message("ITEM-T1", "Paneer Tikka", 4,
                                                                "LOW_STOCK", THRESHOLD)
    _, body_empty = notification_service._build_alert_message("ITEM-T1", "Paneer Tikka", 4,
                                                              "LOW_STOCK", THRESHOLD, [])
    assert "All items currently" not in body_without
    assert body_without == body_empty


def test_list_unavailable_still_sends_the_alert_email(db, monkeypatch):
    monkeypatch.setattr(inventory_service, "_current_low_stock_items",
                        lambda _db, _t: None)            # helper's own failure contract
    inventory_service.create_item(db, item_name="Veg Idly", price=90, total_stock=2)
    assert len(FakeSMTP.all_sent()) == 1
    assert "All items currently" not in _smtp_body()


def test_list_helper_returns_none_on_query_error(db, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("db hiccup")
    monkeypatch.setattr(db, "query", _boom)
    assert inventory_service._current_low_stock_items(db, THRESHOLD) is None
