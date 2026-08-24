# 05 — Software Testing Life Cycle (STLC)

**Project:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform
**New document, written 2026-08-04** as part of the documentation
reorganization, grounded in the real, executable QA pipeline built into
this repo (Newman/Postman, pytest, Allure, Jenkins, Playwright) and the
existing test documentation it summarizes.

---

## 1. Requirement Analysis

Test scope is derived directly from `docs/02_BRS.md` (business objectives,
`BRS-V1-*`/`BRS-V2-*`) and `docs/03_SRS.md` (functional/non-functional
requirements, `FR-*`/`NFR-*`). Every functional and API test case in this
document set traces back to one of those IDs — see `docs/10_RTM.md` for the
full mapping. V1 (the live `app/` platform) and V2 (the documented-only AI
chatbot) are analyzed and planned separately, since they have entirely
different build/verification status — conflating them would misrepresent
what's actually testable today.

## 2. Test Planning

The master plan is `docs/07_Test_Plan.md` — §§1-7 for V1 (real,
executable), §8 for V2 (documented, migrated in from the former
`docs/qa/TP-01-AI-Customer-Support-Chatbot_v1.1.md` during the 2026-08-04
final documentation cleanup; that folder is now retired). Planning defines: what's in scope
(§0 of the Test Plan — `app/` only, legacy/demo code explicitly excluded),
which test levels apply (`docs/06_Test_Strategy.md` §2 — unit,
integration, API/contract, E2E-browser, E2E-order-lifecycle), and how the
plan is executed (manually per the written cases, or automatically via
`Run_QA_Pipeline.bat` / `jenkins/Jenkinsfile`).

## 3. Test Design

Test cases are designed at the following levels, each with its own ID
scheme and home document:

| Level | ID prefix | Document |
|---|---|---|
| Functional | `FUNC-##` | `docs/07_Test_Plan.md` §1 |
| API | `API-##` | `docs/07_Test_Plan.md` §2, `docs/09_API_Test_Cases.md` |
| SQL validation | (queries, not IDs) | `docs/07_Test_Plan.md` §3 |
| Kafka validation | `KAFKA-##` | `docs/07_Test_Plan.md` §4 |
| Negative scenarios | `NEG-##` | `docs/07_Test_Plan.md` §5 |
| Boundary | `BND-##` | `docs/07_Test_Plan.md` §6, `docs/08_Test_Cases.md` |
| Dashboard | `DASH-##` | `docs/07_Test_Plan.md` §6, `docs/08_Test_Cases.md` |
| Smoke | (curated subset) | `docs/07_Test_Plan.md` §6, `docs/16_QA_Automation_Guide.md` |
| V2 Chatbot test cases | `TC-##` | `docs/08_Test_Cases.md` (master; originally sourced from the now-retired `docs/qa/TC-01-...`) |
| V2 Chatbot API | `API-##` (separate namespace) | `docs/09_API_Test_Cases.md` §2 (master; originally sourced from the now-retired `docs/qa/APITEST-01-...`) |

Case-level detail for every ID above: `docs/08_Test_Cases.md` (companion
spreadsheet: `docs/Test_Cases.xlsx`).

## 4. Test Environment Setup

1. `START_OMS360.bat` starts the application stack (MySQL, Zookeeper,
   Kafka, API, consumer). QA tooling never starts Docker or the app
   itself — verification only.
2. `Setup_QA_Environment.bat` — one-time per machine. Verifies Node/npm/
   Java/Python and auto-installs Newman, its reporter plugins, and the
   Allure CLI.
3. Full detail: `docs/15_Installation_Guide.md`, `docs/17_Newman_Setup.md`,
   `docs/18_Allure_Setup.md`.

## 5. Test Execution

`Run_QA_Pipeline.bat` (or `jenkins/Jenkinsfile` in CI) runs the same flow
locally and in CI:

1. Verify the stack is healthy (`postman/verify_stack_health.py`) — fails
   immediately with an explicit message if it isn't, rather than waiting
   or silently continuing.
2. Run Newman (the 56-request/168-assertion Postman collection).
3. Run `pytest` (unit + integration + AI-layer suite).
4. Merge both into one unified Allure report with preserved trend
   history, then apply the dark-theme-by-default cosmetic step.
5. Verify the generated report's structural integrity
   (`postman/verify_allure_report.py`).

Full flow: `docs/06_Test_Strategy.md` §9, `docs/16_QA_Automation_Guide.md`.

## 6. Defect Reporting

Defects are filed in `docs/11_Defect_Report.md` using the project's
standard template (`Student_Practice_Kit/docs/DEFECT_REPORT_TEMPLATE.md`),
numbered sequentially (`DEF-001`, `DEF-002`, ...). Every entry records:
reporter, related test case(s), severity, environment, repro steps,
expected vs. actual result, and status. As of this reorganization, 5
defects are on file — all closed/fixed, none currently open.

## 7. Regression Testing

Run before any sprint is marked Complete, per `docs/06_Test_Strategy.md`
§11 (full checklist, folded in from the former `Regression_Test_Checklist.md`):
all existing unit + integration tests still pass; no previously-fixed
defect has reappeared (cross-checked against `docs/11_Defect_Report.md`);
the full Newman collection passes against the current OpenAPI spec; DB
migrations apply cleanly on fresh and prior schemas; Kafka consumers still
process existing event schema versions without error; dashboards still
render correctly. This is exactly what `Run_QA_Pipeline.bat` and
`jenkins/Jenkinsfile` execute on every run, feeding one Allure report so a
regression is visible immediately rather than assumed passed.

## 8. Test Closure

A test cycle closes when `docs/12_Test_Summary_Report.md` is updated to
reflect the real, executed results (never claiming a pass that wasn't
actually run — the standing ethos of that document), open defects in
`docs/11_Defect_Report.md` are resolved or explicitly deferred with
rationale, and the Release Checklist in `docs/06_Test_Strategy.md` §12 is
complete. As of this reorganization, closure is **partial**: `pytest`
(393/393), Newman (56 requests/168 assertions), and Allure report
generation are all confirmed executed and passing; Playwright run #1
(141/142) surfaced one test-authoring defect (`DEF-004`, fixed but not
yet re-confirmed with a second run); and a documented list of runtime
checks (Kafka validation, load/performance testing, a clean-machine
Docker startup pass) remain **not yet executed** — see
`docs/12_Test_Summary_Report.md` §2 for the full, honest list.
