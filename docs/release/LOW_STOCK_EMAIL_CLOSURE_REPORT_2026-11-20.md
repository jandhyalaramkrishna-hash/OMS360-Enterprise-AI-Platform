# OMS360 — Low-Stock Email Notification Fix — Closure Report

| Field | Value |
|---|---|
| Project | Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform |
| Organization | ZelQA Technologies |
| Project Owner | Ramakrishna Jandhyala |
| Change | Low-stock / out-of-stock inventory alert email notification fix |
| Defect reference | DEF-006 (`docs/11_Defect_Report.md`) |
| Decision reference | DEC-0034 (`docs/governance/DECISION-LOG.md`) |
| Date | 2026-11-20 (IST) |
| Environment | Local Docker Desktop (Windows) — `oms360_core_engine`, `oms360_consumer`, `oms360_mysql`, Kafka |
| Final status | **CLOSED — Functionally validated (automated + live)** |

---

## 1. Summary

Inventory alert emails for low-stock / out-of-stock items had stopped arriving. Five code defects in the notification and inventory alert flow were fixed, 33 new automated tests were added, and the fix was deployed to the local Docker environment and validated with 41 automated tests and one controlled live Gmail delivery. No database schema, migration, Kafka configuration or inventory data was changed, and the working Gmail SMTP configuration was left as-is.

## 2. Root causes

### 2.1 Code defects (fixed in application code)

1. **Delivery outcome recorded wrongly.** Every not-sent case — including "notifications feature disabled" — was stored as `FAILED`, so "never attempted" could not be distinguished from "Gmail rejected the login", and nothing ever retried. Now: `PENDING` (feature off, not attempted), `SENT` (SMTP accepted), `FAILED` (attempted, not delivered).
2. **Email sent inside the open order transaction.** SMTP ran while inventory rows were locked `FOR UPDATE`, and a transaction that later rolled back could already have emailed about an alert row that no longer existed. Now alerts are queued and emailed only after commit.
3. **Duplicate alerts and emails.** Every reservation below the threshold inserted another alert row and sent another email. Now one alert (and one email) per low-stock / out-of-stock episode; unsent alerts are retried instead of duplicated.
4. **No way to deliver undelivered alerts.** Alerts recorded while notifications were disabled or SMTP was failing could never be sent. Added `POST /api/v1/inventory/alerts/dispatch-pending` and a cooldown-based automatic retry (`OMS360_NOTIFICATION_RETRY_COOLDOWN_SECONDS`, default 300 s).
5. **SMTP robustness and log hygiene.** Stray whitespace / CR from a CRLF `.env` is trimmed from the SMTP password before login; SMTP failures are classified (authentication / recipient refused / connection) and logged without credentials (password never logged, username masked). OUT_OF_STOCK alerts now have distinct subject/body wording.

### 2.2 Deployment issue (no file change needed)

The container was recreated with `docker compose up -d --force-recreate oms360-engine`, which reuses the **existing image** and does not rebuild it. The Dockerfile copies `app/` and `tests/` into the image at build time and Compose mounts no source folders, so the running container had neither the new test file (`pytest: file or directory not found`) nor the fixed application code. Resolved by rebuilding the `oms360-engine` and `oms360-consumer` images.

## 3. Files changed

| File | Change |
|---|---|
| `app/services/notification_service.py` | `send_low_stock_alert()` with PENDING/SENT/FAILED outcome; OUT_OF_STOCK wording; classified, credential-free error logging; password trimming. `notify_low_stock()` kept for backward compatibility. |
| `app/services/inventory_service.py` | Alerts queued and dispatched after commit; per-episode de-duplication; cooldown retry; `dispatch_open_alerts()`. |
| `app/services/order_service.py` | Calls `dispatch_pending_notifications()` after the order transaction commits. |
| `app/routes/inventory.py` | New `POST /api/v1/inventory/alerts/dispatch-pending`. |
| `app/config.py` | `EMAIL_SMTP_TIMEOUT_SECONDS`, `NOTIFICATION_RETRY_COOLDOWN_SECONDS`. |
| `.env.example` | Documents the two optional settings above (no secrets). |
| `tests/test_inventory_notifications.py` | New — 33 self-contained tests (in-memory SQLite, fake SMTP, no real email). |
| `scripts/dispatch_single_alert.py` | New — one-off ops script used for the controlled live test (see §5). |

Not changed: database schema, migrations, Kafka configuration, Dockerfile, `docker-compose.yml`, `.env` (git-ignored; holds the working Gmail App Password), inventory data.

## 4. Automated test results — PASS

Executed inside `oms360_core_engine` after the image rebuild.

| Suite | Passed | Failed | Skipped | Notes |
|---|---|---|---|---|
| `tests/test_inventory_notifications.py` (new) | 33 | 0 | 0 | SQLite + fake SMTP; no real email sent |
| `tests/test_inventory.py` (existing) | 8 | 0 | 0 | Live MySQL; run with `OMS360_FEATURE_NOTIFICATIONS=false` so no real email was sent |
| **Total** | **41** | **0** | **0** | |

The 33 notification tests were also executed independently on Python 3.10 with the project's pinned `requirements.txt` before deployment — 33 passed.

## 5. Live integration test — LIT-NOTIF-001 — PASS

| Field | Value |
|---|---|
| Test ID | LIT-NOTIF-001 — Live Gmail delivery of a single inventory alert |
| Objective | Prove an alert email is delivered through Gmail SMTP end to end, for exactly one alert, without bulk dispatch |
| Method | `Get-Content scripts\dispatch_single_alert.py -Raw \| docker exec -i oms360_core_engine python -` — calls the existing `inventory_service._deliver_alert()` (same code path as `dispatch-pending`) for alert 12 only |
| Pre-checks in script | Notifications flag enabled; recipient = `jandhyala.ramkrishna@gmail.com`; alert 12 is for `ITEM-1053` and is PENDING/FAILED — otherwise aborts before any SMTP connection |
| SMTP | `smtp.gmail.com:587`, STARTTLS, Gmail App Password authentication — PASS |
| Alert | ID 12 — `ITEM-1053` — LOW_STOCK — remaining stock 3 — threshold 5 |
| Recipient | `jandhyala.ramkrishna@gmail.com` |
| SMTP result | **SENT** (Gmail accepted the message) |
| Email received | Yes — confirmed by Project Owner |
| Alert 12 status | PENDING → **SENT** |
| Emails sent | **Exactly 1** — no duplicates |
| Inventory | `ITEM-1053` remaining stock unchanged at 3 |
| Other alerts | 5, 6, 13 unchanged (PENDING) |
| Credentials | Not printed or logged |
| Bulk `dispatch-pending` | Not invoked |
| Result | **PASS** |

## 6. Overall validation checklist

| # | Check | Result |
|---|---|---|
| 1 | Gmail SMTP authentication | PASS |
| 2 | Docker engine and consumer rebuild | PASS |
| 3 | Application health check | PASS |
| 4 | New notification automated tests (33) | PASS |
| 5 | Existing inventory tests (8) | PASS |
| 6 | Actual Gmail email delivery | PASS |
| 7 | Single-alert dispatch (alert 12 only) | PASS |
| 8 | Database integrity (alert 12 SENT; 5, 6, 13 unchanged; stock unchanged) | PASS |

## 7. Remaining pending alerts — documented, NOT sent

| Alert ID | Item ID | Alert type | Notification status | Recipient on record | What will happen next |
|---|---|---|---|---|---|
| 5 | ITEM-1021 | OUT_OF_STOCK | PENDING | NULL | Sent only by `dispatch-pending` while ITEM-1021 is still at 0 stock (an out-of-stock item cannot be ordered, so no order will trigger it). |
| 6 | ITEM-1033 | LOW_STOCK | PENDING | NULL | Sent automatically on the next order or stock correction that leaves ITEM-1033 still low, or by `dispatch-pending`. |
| 13 | ITEM-1059 | LOW_STOCK | PENDING | jandhyala.ramkrishna@gmail.com | Same as alert 6, for ITEM-1059. |

Notes:
- A NULL recipient is not a fault: delivery always uses the currently configured `OMS360_INVENTORY_ALERT_EMAIL` and records it on the alert when sent.
- All three items use auto-generated item numbers (`ITEM-10xx`), the pattern produced by "Add New Item" and by the inventory test suite, so they are likely QA test items. The Project Owner should decide whether they should ever be emailed before anyone calls `dispatch-pending`.
- Calling `POST /api/v1/inventory/alerts/dispatch-pending` would send up to three emails (one per alert above) as long as each item is still at the matching stock level.

## 8. Behaviour notes for operations

- **Threshold:** the live database has `LOW_STOCK_THRESHOLD = 5` in `system_configuration` (code default is 10 when no row exists). Items at or below 5 are LOW_STOCK; at 0 they are OUT_OF_STOCK.
- **One email per episode:** an item that is already LOW_STOCK and already emailed does not email again on later orders. A new email is sent when it becomes OUT_OF_STOCK, or after it is restocked above the threshold and drops again.
- **Deploying code changes:** use `docker compose up -d --build` (as `START_OMS360.bat` does) or `docker compose build` first. `--force-recreate` alone does not pick up code changes.
- **Running `tests/test_inventory.py` in the container:** use `docker exec -e OMS360_FEATURE_NOTIFICATIONS=false …` so its LOW_STOCK test item does not trigger a real email. The suite adds new "QA Test Item" rows by design; it does not modify existing items.

## 9. Remaining issues / follow-ups (non-blocking)

1. Decide what to do with pending alerts 5, 6 and 13 (send, or leave as historical test data).
2. The production image still contains pytest, httpx and `tests/` (by existing design, to support `docker exec … pytest`). A multi-stage Dockerfile could remove them later; not done here to avoid an architecture change.
3. Unrelated uncommitted local changes remain outside this fix and were deliberately excluded from the commit: `app/routes/dashboard.py` (timezone), `app/routes/metrics.py` (+ `.bak`), `START_OMS360.bat`, `scripts/common.bat`, `sql start command.txt`, `docker-compose.monitoring.yml`, `monitoring/`, Allure / Postman report output.
4. `docs/governance/DECISION-LOG.md` headings stop at DEC-0010 while code comments reference DEC-0011…DEC-0033; this fix uses DEC-0034 to avoid collisions. Back-filling the missing entries is a separate documentation task.
5. `docs/governance/MODULE-STATUS.md` is largely stale (most V1 modules still read "Not Started"); only the Notification Service row was updated here.

## 10. Git

Commit prepared locally (not pushed — awaiting Project Owner approval). Scope: the 8 files in §3 plus the documentation updates listed below.

Documentation updated:
- `docs/release/LOW_STOCK_EMAIL_CLOSURE_REPORT_2026-11-20.md` (this report — new)
- `docs/12_Test_Summary_Report.md` — §8 addendum
- `docs/11_Defect_Report.md` — DEF-006
- `docs/governance/DECISION-LOG.md` — DEC-0034
- `docs/release/SPRINT-LOG.md` — 2026-11-20 entry
- `docs/governance/MODULE-STATUS.md` — Notification Service row

---

**Closure:** The low-stock / out-of-stock email notification fix is functionally validated by 41 passing automated tests and one successful live Gmail delivery (LIT-NOTIF-001). Status: **CLOSED**.

Prepared for: Ramakrishna Jandhyala, Project Owner — ZelQA Technologies
