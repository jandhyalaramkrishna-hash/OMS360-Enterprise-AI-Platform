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
THRESHOLD = 10                      # inventory_service.DEFAULT_LOW_STOCK_THRESHOLD


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


def _add_item(db, item_id="ITEM-T1", stock=12, status="ACTIVE", name="Paneer Tikka"):
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
                                                       alert_type="LOW_STOCK", threshold=10)
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
    _add_item(db, stock=12)
    summary = _reserve(db, "ITEM-T1", 3)                       # 12 -> 9 (<= 10)
    alerts = _alerts(db)
    assert len(alerts) == 1
    a = alerts[0]
    assert (a.alert_type, a.notification_status, a.recipient_email) == ("LOW_STOCK", "SENT", TEST_RECIPIENT)
    assert (a.remaining_stock, a.threshold_value) == (9, THRESHOLD)
    assert summary["sent"] == 1 and len(FakeSMTP.all_sent()) == 1
    assert FakeSMTP.all_sent()[0][1] == [TEST_RECIPIENT]
    assert db.get(models.Inventory, "ITEM-T1").status == "LOW_STOCK"


def test_email_is_not_sent_before_the_transaction_commits(db):
    _add_item(db, stock=12)
    row = inventory_service.lock_and_fetch(db, ["ITEM-T1"])["ITEM-T1"]
    inventory_service.reserve_stock(db, "ITEM-T1", row, 3, "ORD-1")
    assert FakeSMTP.instances == []                            # nothing sent mid-transaction
    db.commit()
    inventory_service.dispatch_pending_notifications(db)
    assert len(FakeSMTP.all_sent()) == 1


def test_rolled_back_transaction_sends_no_email(db):
    _add_item(db, stock=12)
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
    _add_item(db, stock=12)
    _reserve(db, "ITEM-T1", 3, "ORD-1")                        # 9  -> alert + email
    _reserve(db, "ITEM-T1", 1, "ORD-2")                        # 8
    _reserve(db, "ITEM-T1", 2, "ORD-3")                        # 6
    assert len(_alerts(db)) == 1
    assert len(FakeSMTP.all_sent()) == 1


def test_same_item_twice_in_one_transaction_creates_single_alert(db):
    _add_item(db, stock=12)
    row = inventory_service.lock_and_fetch(db, ["ITEM-T1"])["ITEM-T1"]
    inventory_service.reserve_stock(db, "ITEM-T1", row, 3, "ORD-1")
    inventory_service.reserve_stock(db, "ITEM-T1", row, 1, "ORD-1")
    db.commit()
    inventory_service.dispatch_pending_notifications(db)
    assert len(_alerts(db)) == 1 and len(FakeSMTP.all_sent()) == 1


def test_low_to_out_of_stock_sends_out_of_stock_notification(db):
    _add_item(db, stock=12)
    _reserve(db, "ITEM-T1", 3)                                 # LOW_STOCK
    _reserve(db, "ITEM-T1", 9)                                 # 0 -> OUT_OF_STOCK
    alerts = _alerts(db)
    assert [a.alert_type for a in alerts] == ["LOW_STOCK", "OUT_OF_STOCK"]
    assert all(a.notification_status == "SENT" for a in alerts)
    assert len(FakeSMTP.all_sent()) == 2
    assert "OUT OF STOCK" in FakeSMTP.all_sent()[1][2] or "OUT_OF_STOCK" in FakeSMTP.all_sent()[1][2]
    assert db.get(models.Inventory, "ITEM-T1").status == "OUT_OF_STOCK"


def test_direct_active_to_out_of_stock_sends_one_email(db):
    _add_item(db, stock=12)
    _reserve(db, "ITEM-T1", 12)
    assert [a.alert_type for a in _alerts(db)] == ["OUT_OF_STOCK"]
    assert len(FakeSMTP.all_sent()) == 1


def test_smtp_failure_marks_failed_then_retries_after_cooldown_without_new_row(db, monkeypatch):
    _add_item(db, stock=12)
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
    _add_item(db, stock=12)
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
                                 threshold_value=10, alert_type="LOW_STOCK", notification_type="EMAIL",
                                 notification_status="FAILED", recipient_email=TEST_RECIPIENT))
    # Stale alert for an item that has since been restocked - must be ignored.
    _add_item(db, item_id="ITEM-T2", stock=80, name="Lassi")
    db.add(models.InventoryAlert(item_id="ITEM-T2", item_name="Lassi", remaining_stock=2,
                                 threshold_value=10, alert_type="LOW_STOCK", notification_type="EMAIL",
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
    _add_item(db, stock=6, status="LOW_STOCK")                 # e.g. seeded/manual status
    _reserve(db, "ITEM-T1", 1)
    assert len(_alerts(db)) == 1 and len(FakeSMTP.all_sent()) == 1


def test_recipient_comes_from_current_configuration(db, monkeypatch):
    monkeypatch.setattr(settings, "INVENTORY_ALERT_EMAIL", "")
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", True)
    _add_item(db, stock=12)
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

    _reserve(db, "ITEM-T1", 35)                                 # 8 -> new LOW_STOCK episode
    assert [a.alert_type for a in _alerts(db)] == ["LOW_STOCK", "LOW_STOCK"]
    assert len(FakeSMTP.all_sent()) == 2


def test_update_item_recover_to_active_still_works(db):
    _add_item(db, stock=5, status="LOW_STOCK")
    row = inventory_service.update_item(db, "ITEM-T1", stock=500)
    assert row.status == "ACTIVE" and FakeSMTP.instances == []


def test_restock_partial_from_low_stays_low(db):
    _add_item(db, stock=12)
    _reserve(db, "ITEM-T1", 6)                                  # 6, LOW_STOCK
    inventory_service.restock(db, "ITEM-T1", 2)                 # 8, still <= 10
    assert db.get(models.Inventory, "ITEM-T1").status == "LOW_STOCK"
    _reserve(db, "ITEM-T1", 1)
    assert len(FakeSMTP.all_sent()) == 1                        # still same episode


def test_release_stock_above_threshold_recovers_status(db):
    _add_item(db, stock=12)
    _reserve(db, "ITEM-T1", 5)                                  # 7, LOW_STOCK
    row = inventory_service.lock_and_fetch(db, ["ITEM-T1"])["ITEM-T1"]
    inventory_service.release_stock(db, "ITEM-T1", row, 5, "ORD-1", "Cancelled")
    db.commit()
    assert db.get(models.Inventory, "ITEM-T1").status == "ACTIVE"


def test_no_password_in_logs_across_full_failure_flow(db, captured_logs):
    _add_item(db, stock=12)
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
    _add_item(db, stock=12)
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
