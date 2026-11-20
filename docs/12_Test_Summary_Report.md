# 12 — Test Summary Report — OMS-360

**Consolidated:** 2026-08-04 (renumbered from `docs/Test_Summary_Report.md`,
content unchanged), from `docs/FINAL_RELEASE_REPORT.md` (V1.2 packaging +
AI Platform v1.0.0 addendum, left in place as the full 400+ line source of
record), `PLAYWRIGHT_EXECUTION_REPORT.md` (kept at `docs/` root — unique,
not a duplicate), and the Newman/Allure QA pipeline work. This report
follows the project's own stated ethos: **nothing here claims a test
passed unless it was actually executed** — anything not executed is
explicitly marked as such.

## 1. What Has Actually Been Executed (real, confirmed results)

| Suite | Result | Source |
|---|---|---|
| `pytest` — AI Enterprise Platform (`ai/`), cumulative through Sprint 9 | **393/393 passing** | `docs/VERSION-HISTORY.md` v1.0.0 entry, `docs/FINAL_RELEASE_REPORT.md` Addendum §A4 |
| Playwright — full suite, run #1, 2026-08-03 | **141/142 passing** (1 test-authoring defect, since fixed — `docs/11_Defect_Report.md` DEF-004) | `PLAYWRIGHT_EXECUTION_REPORT.md` |
| Newman/Postman — 56 requests, 168 assertions | **Confirmed executing successfully** on Ram's machine, 2026-08-04 (CLI/HTML/JSON/JUnit reports all generate) | User confirmation |
| Allure report generation | **Confirmed structurally sound and confirmed rendering correctly** — real result files, metadata, history, and generated report data all verified present and well-formed via direct file inspection, and confirmed visually (100% pass, 56 tests, all tabs, dark theme) by the Product Owner | `docs/governance/QA_ALLURE_500_FIX_2026-08-04.md` |

## 2. What Is Documented but NOT Yet Executed (requires local verification)

Per `docs/FINAL_RELEASE_REPORT.md` §3 (13 items — Windows/Docker/MySQL
runtime checks that could not be executed in a sandbox with no Docker/
Windows access): full `.bat` launcher script runs, Docker build, full
stack startup order on a clean machine, Swagger/dashboard manual checks,
`/health` returning `HEALTHY` (not just 200), the Create Order → SQL
validation path, Kafka publish/consume/DLQ end-to-end, inventory
deduction, dashboard live updates, `STOP`/`RESTART`/`CHECK` script
behavior, and the manual application of migration `003`.

Also not yet executed: `docs/07_Test_Plan.md` §4 (Kafka validation) is
entirely manual with no automated equivalent (see `docs/06_Test_Strategy.md`
§10); a Playwright run #2 confirming the DEF-004 fix holds; and any load/
performance test (`docs/06_Test_Strategy.md` §7).

## 3. Playwright Run #1 Detail (2026-08-03)

| Metric | Value |
|---|---|
| Total Tests | 142 |
| Passed | 141 |
| Failed | 1 (`tests/api/health.spec.ts` — DEF-004, fixed same day) |
| Skipped | 0 |
| Environment | `http://localhost:8000`, full Docker Compose stack confirmed healthy |
| Browser | Chromium (Desktop Chrome profile) |

**Open follow-up:** re-run `tests/api/health.spec.ts` alone, then the full
suite, to confirm the DEF-004 fix holds and produce Run #2's real numbers.
Command: `npx playwright test` from `playwright/` (or `RUN_PLAYWRIGHT.bat`).

## 4. QA Pipeline Verification (2026-08-04)

The Newman/Postman + pytest/Allure + Jenkins pipeline built in this
project was verified against Ram's real 10-point requirement list for
Allure integration (full detail: `docs/governance/QA_ALLURE_500_FIX_2026-08-04.md`):

| # | Requirement | Verdict |
|---|---|---|
| 1-4, 6-7 | Newman/pytest write valid Allure results; metadata files correct; history preserved; `allure generate` succeeds | **Confirmed** via direct file inspection (real result/attachment file counts, byte-verified metadata content, populated history/trend data) |
| 5 | Stop and print exact error if `allure generate` fails | **Fixed** — `Generate_Allure_Report.bat` now checks the exit code explicitly |
| 8 | Report opens correctly | **Root cause fixed** — `file://` CORS issue; `Run_QA_Pipeline.bat` now uses `allure open` |
| 9 | No FastAPI/business logic modified | **Confirmed** — QA tooling only |
| 10 | Full report renders all tabs correctly | **Confirmed** — Product Owner visually verified 100% pass, 56 tests, all tabs, dark theme applied |

## 5. Quality Gate Status (from `docs/FINAL_RELEASE_REPORT.md` §6)

| Check | Status |
|---|---|
| No placeholder values in packaging/launcher files | Pass |
| Ports/env vars match actual source | Pass |
| Compose dependencies correct (textual review) | Pass |
| Build/runtime success | Requires local verification |
| No container conflicts | Requires local verification |
| Documentation complete | Pass |

## 6. Known Limitations Carried Forward (not defects — documented gaps)

No authentication on any route. Delivery OTP/GPS are client-side
simulations. In-memory metrics reset on restart. Idempotency cache is
in-process only. AI Enterprise Platform is fully mock-based (no real
vendor LLM/vector DB/MCP transport/agent runtime/eval service). Full
list: `docs/02_BRS.md` §1.6.

## 7. Recommendation

Before this project can be called fully runtime-verified end to end, the
13 items in §2 need a real execution pass on the target machine, plus a
confirmed-clean Playwright run #2. Everything currently claimed as
"executed" above is real, sourced, and cited — nothing in this report
extrapolates a pass from a code review alone.

## 8. Addendum 2026-11-20 — Low-Stock Email Notification Fix (executed, real results)

Executed on the Project Owner's machine in the local Docker environment
after rebuilding the `oms360-engine` / `oms360-consumer` images. Full
evidence: `docs/release/LOW_STOCK_EMAIL_CLOSURE_REPORT_2026-11-20.md`.
Defect: `docs/11_Defect_Report.md` DEF-006.

### 8.1 Automated tests — PASS

| Suite | Passed | Failed | Skipped | Source |
|---|---|---|---|---|
| `tests/test_inventory_notifications.py` (new; SQLite + fake SMTP, no real email) | **33** | 0 | 0 | `docker exec oms360_core_engine python -m pytest …`, 2026-11-20 |
| `tests/test_inventory.py` (existing; live MySQL, run with `OMS360_FEATURE_NOTIFICATIONS=false`) | **8** | 0 | 0 | same run |
| **Total** | **41** | **0** | **0** | |

### 8.2 Live integration test — LIT-NOTIF-001 — PASS

| Field | Result |
|---|---|
| Scope | One inventory alert email through real Gmail SMTP (`smtp.gmail.com:587`, STARTTLS, App Password) |
| Method | `scripts/dispatch_single_alert.py` piped into `oms360_core_engine` — existing `_deliver_alert()` code path, alert 12 only; bulk `dispatch-pending` not invoked |
| Alert | ID 12 — ITEM-1053 — LOW_STOCK — stock 3 — threshold 5 |
| SMTP result | SENT — email received at jandhyala.ramkrishna@gmail.com |
| Emails sent | Exactly 1 |
| Database | Alert 12 PENDING → SENT; alerts 5, 6, 13 unchanged (PENDING); ITEM-1053 stock unchanged (3) |
| Credentials in logs | None |

Pending alerts 5, 6 and 13 were deliberately not sent; see the closure
report §7.
