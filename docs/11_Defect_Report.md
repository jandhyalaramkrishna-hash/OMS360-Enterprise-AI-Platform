# 11 — Defect Report — OMS-360

**Consolidated:** 2026-08-04 (renumbered from `docs/Defect_Report.md`,
content unchanged). Format follows the project's standard defect template
(`Student_Practice_Kit/docs/DEFECT_REPORT_TEMPLATE.md`, left in place — it
ships with the practice kit). This document files the real defects found
and fixed across this project's history — pulled from `README.md`'s
Backend Stability Audit, `PLAYWRIGHT_EXECUTION_REPORT.md`, and QA-tooling
fixes — as structured, queryable records instead of only prose in change
logs.

All defects below are **CLOSED / FIXED**. None are currently open. New
defects found in future test runs should be appended here using the same
template, numbered sequentially from `DEF-007`.

---

## DEF-001

**Reported by:** Backend Stability Audit, 2026-07-22
**Related test case(s):** Application startup / import verification
**Severity:** Critical — app won't start

### Summary
`app/models.py` had an undefined-name crash on import — the application
could not start at all.

### Environment
OMS360 v1.2 business platform, all environments.

### Steps to Reproduce
1. Start the FastAPI application (`uvicorn app.main:app` or via Docker).
2. Import chain reaches `app/models.py`.

### Expected Result
Application imports and starts successfully.

### Actual Result
ImportError / NameError on an undefined name, application fails to boot.

### Status
**FIXED** — code fix applied to `app/models.py`. See
`docs/governance/DECISION-LOG.md` for the full decision record.

---

## DEF-002

**Reported by:** Backend Stability Audit, 2026-07-22
**Related test case(s):** `docs/07_Test_Plan.md` §3 (SQL Validation)
**Severity:** High — a core feature doesn't work as documented

### Summary
Three ORM columns were mapped to database column names that don't exist
in `database/oms360_schema.sql` (`grand_total`, `created_at`,
`cooking_status`).

### Environment
OMS360 v1.2 business platform, MySQL persistence layer.

### Steps to Reproduce
1. Trigger any ORM operation touching the affected columns.
2. Observe the resulting SQL error against the real schema.

### Expected Result
ORM column mappings match the real schema exactly.

### Actual Result
Mismatched column names would cause a runtime SQL error on the affected
operations.

### Status
**FIXED** — ORM mappings corrected to match `database/oms360_schema.sql`
exactly. Schema itself was not modified (source-of-truth policy).

---

## DEF-003

**Reported by:** Backend Stability Audit, 2026-07-22
**Related test case(s):** `docs/15_Installation_Guide.md` §1 (Docker startup)
**Severity:** Critical — data loss risk

### Summary
`docker-compose.yml`'s MySQL init-script mount pointed at a nonexistent
path, so the master schema was likely never actually applied to the
`oms360_mysql_data` volume on a fresh environment.

### Environment
Fresh Docker Compose environment, first-time startup.

### Steps to Reproduce
1. `docker compose up -d mysql` on a machine that has never run this
   project before.
2. Inspect whether `oms360_schema.sql` was applied.

### Expected Result
Schema auto-applies via the `docker-entrypoint-initdb.d` mount on first
boot.

### Actual Result
Init-script mount path did not resolve to the real schema file location —
schema may silently fail to apply.

### Status
**FIXED** — `docker-compose.yml` mount path corrected. `database/oms360_schema.sql`
itself was not modified.

---

## DEF-004

**Reported by:** Playwright execution run #1, 2026-08-03
**Related test case(s):** `tests/api/health.spec.ts`
**Severity:** Low — test-authoring defect, not an application defect

### Summary
`tests/api/health.spec.ts`'s "GET /health returns overall status +
dependency map" test asserted `body.dependencies` contains a key named
`kafka`. It does not, and never did — the real `dependencies` dict has 13
keys (`application`, `database`, `kafka_broker`, `kafka_producer`,
`kafka_consumer_group`, `disk`, `memory`, `cpu`, `docker`, `redis`,
`build_version`, `environment`, `db_pool`), with Kafka status
intentionally split into three real keys, not merged into one.

### Environment
Playwright suite, `http://localhost:8000`, Docker Compose stack healthy
(MySQL, Zookeeper, Kafka, oms360-engine, oms360-consumer all confirmed
healthy at run time).

### Steps to Reproduce
1. Run `npx playwright test tests/api/health.spec.ts` against a healthy stack.
2. Observe the assertion on `body.dependencies.kafka`.

### Expected Result
Test asserts the real, complete 13-key `dependencies` contract.

### Actual Result
Test asserted a 3-key subset including a nonexistent `kafka` key —
grounded in `SystemHealthResponse`'s illustrative docstring example rather
than the real `health()` route handler.

### Evidence
1 of 142 total Playwright tests failed in the 2026-08-03 run (141/142 passing).

### Status
**FIXED (test-only)** — `tests/api/health.spec.ts` now asserts the
complete, real 13-key set and additionally asserts `kafka` is *not*
present. `app/` was not touched. **Not yet re-confirmed with a second run**
— see `docs/12_Test_Summary_Report.md` §3 for the open follow-up.

---

## DEF-005

**Reported by:** Ram (production QA pipeline usage), 2026-08-04
**Related test case(s):** Newman/Allure QA pipeline execution
**Severity:** Medium — a core feature (report viewing) didn't work as documented, with a workaround

### Summary
Two related QA-tooling defects, found and fixed the same day:
(a) `postman/run-newman.bat` passed an unquoted comma-separated
`--reporters` value through PowerShell, which parsed it as an array
literal and re-stringified it with spaces, corrupting it into one bogus
reporter name; (b) `allure-report/index.html` showed "500 Failed to
fetch" when opened directly (`file://` CORS blocking the report's own
`fetch()` calls to its data files), and `Generate_Allure_Report.bat`
never checked `allure generate`'s own exit code, so a future real
generation failure would have been silently swallowed.

### Environment
Windows, real project machine, `postman/run-newman.bat` /
`Generate_Allure_Report.bat` / `Run_QA_Pipeline.bat`.

### Steps to Reproduce
(a) Run `Run_QA_Pipeline.bat` or `postman/run-newman.bat` with the
unquoted `--reporters cli,json,htmlextra,junit,allure` value.
(b) Run the full pipeline successfully, then double-click
`allure-report/index.html` or let `Run_QA_Pipeline.bat`'s old auto-open
line do it via `start`.

### Expected Result
(a) Newman runs with all 5 reporters active. (b) The Allure report opens
and every tab (Overview/Suites/Behaviors/Categories/Timeline/Graphs/
Environment) renders real data.

### Actual Result
(a) `newman: could not find "cli json htmlextra junit allure" reporter`.
(b) Blank page / "500 Failed to fetch" despite the report having
genuinely generated correctly (verified via file-level evidence — see
`docs/governance/QA_ALLURE_500_FIX_2026-08-04.md`).

### Status
**FIXED.** (a) `--reporters` value single-quoted as one PowerShell
string literal. (b) `Run_QA_Pipeline.bat` now opens the report via
`allure open allure-report` (a real local HTTP server) instead of a
direct `file://` open; `Generate_Allure_Report.bat` now checks
`allure generate`'s exit code and stops immediately with the exact error
if it fails, then runs `postman/verify_allure_report.py` integrity check
before declaring success. Full detail:
`docs/governance/QA_ALLURE_500_FIX_2026-08-04.md`.

---

## DEF-006

**Reported by:** Project Owner (Ramakrishna Jandhyala), 2026-11-20
**Related test case(s):** `tests/test_inventory_notifications.py` (33 tests), `tests/test_inventory.py`, LIT-NOTIF-001
**Severity:** High — inventory alert emails not delivered

### Summary
Low-stock / out-of-stock inventory alert emails stopped arriving, and
alerts recorded while notifications were off or SMTP was failing could
never be delivered.

### Root Cause
Five code defects plus one deployment issue:
1. Every not-sent outcome (including "feature disabled") was stored as
   `FAILED`; no retry existed.
2. Email was sent inside the open order transaction (rows locked
   `FOR UPDATE`); a rolled-back transaction could already have emailed.
3. Every reservation below the threshold created another alert row and
   another email.
4. No mechanism to deliver alerts left undelivered.
5. Stray whitespace / CR in the SMTP password from a CRLF `.env`;
   unclassified SMTP error logging.
6. Deployment: `docker compose up -d --force-recreate` reused the old
   image, so the container had neither the fixed code nor the new tests
   (`pytest: file or directory not found`).

### Steps to Reproduce
Enable `OMS360_FEATURE_NOTIFICATIONS`, configure Gmail SMTP, place orders
that take an item to or below `LOW_STOCK_THRESHOLD`.

### Expected Result
One alert email per low-stock / out-of-stock episode, delivered after the
order commits; `inventory_alerts.notification_status` reflects the true
outcome.

### Actual Result
No email received; alert rows left in an inaccurate state, with
duplicates per order.

### Status
**FIXED / CLOSED — 2026-11-20.** PENDING/SENT/FAILED outcomes, post-commit
dispatch, per-episode de-duplication, cooldown retry, new
`POST /api/v1/inventory/alerts/dispatch-pending`, credential-safe logging.
Images rebuilt. Verified: 41/41 automated tests passed; live Gmail
delivery LIT-NOTIF-001 passed (alert 12 SENT, exactly one email). Full
evidence: `docs/release/LOW_STOCK_EMAIL_CLOSURE_REPORT_2026-11-20.md`.
