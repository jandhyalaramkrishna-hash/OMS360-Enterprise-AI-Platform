# QA_DOCUMENT_INVENTORY.md — OMS-360 / Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

**Originally generated:** 2026-08-03. **Updated:** 2026-08-04 — full
documentation consolidation pass completed (see
`docs/governance/QA_DOCS_CONSOLIDATION_2026-08-04.md` for the full
before/after record).

## Current State (2026-08-04)

The standard, requested QA document set now exists at `docs/` root:

| File | Consolidated from |
|---|---|
| `BRS.md` | `docs/business/BR-01-...`, `docs/business/US-01-...`, project description, README |
| `SRS.md` | `docs/architecture/00_Architecture_Understanding_v1.0.md`, `Feature-01`, `API-01`, `DB-01`, `KAFKA-01` |
| `Test_Plan.md` | `docs/TEST_PLAN.md` (V1, real, 39 cases) + pointer to `docs/qa/TP-01-...` (V2) |
| `Test_Strategy.md` | `docs/qa/QA-STANDARDS.md` + the real Newman/pytest/Allure/Jenkins/Playwright tooling |
| `Test_Cases.xlsx` | All of the above test-case documents, consolidated into one multi-sheet workbook, **new 2026-08-04** |
| `RTM.xlsx` | **New 2026-08-04** — this project's first Requirements Traceability Matrix |
| `Defect_Report.md` | README's Backend Stability Audit + `PLAYWRIGHT_EXECUTION_REPORT.md` + this session's own QA-tooling fixes — 5 real, closed defects filed against the standard template |
| `Test_Summary_Report.md` | `docs/FINAL_RELEASE_REPORT.md` + `PLAYWRIGHT_EXECUTION_REPORT.md` + the QA pipeline verification |
| `API_Test_Cases.md` | The real 56-request/168-assertion Newman collection + `docs/qa/APITEST-01-...` (V2) |
| `Smoke_Test_Checklist.md` | `TC-GAP-01-Missing-Coverage.md` §2, reformatted as an actual checklist |
| `Regression_Test_Checklist.md` | `docs/qa/QA-STANDARDS.md` §9 + `docs/qa/REG-01-...` (V2) |
| `Release_Notes.md` | Reader-facing distillation of `VERSION-HISTORY.md` |
| `User_Guide.md` | End-user-oriented guide, references `docs/RUN_GUIDE.md` for deep technical detail |

Also migrated to `docs/` root (unique content, previously only in
`docs/QA_Documents/`): `TEST_CASE_COVERAGE.md`,
`PLAYWRIGHT_EXECUTION_REPORT.md`, `TC-GAP-01-Missing-Coverage.md`.

## What Was Removed

`docs/QA_Documents/` (16 files: 13 exact/near-exact copies of documents
still in place elsewhere, now retired; 3 unique files, migrated above
before removal) — see `Cleanup_Duplicate_Docs.bat` at the project root,
which a human must run once (this session's device-bridge tooling can
write files but not delete them — see the governance doc for why).

## What Was Deliberately Left in Place (not duplicates)

- `docs/qa/*`, `docs/business/*`, `docs/architecture/*` — the detailed,
  authoritative V2 chatbot specs. The new root-level docs (BRS/SRS/
  Test_Plan/etc.) summarize and reference these; they don't duplicate
  them wholesale, so re-typing them would create the same problem this
  cleanup fixed.
- `docs/FINAL_RELEASE_REPORT.md`, `docs/RUN_GUIDE.md`, `VERSION-HISTORY.md`
  — full-detail source documents the new root docs summarize.
- `Student_Practice_Kit/docs/TEST_CASES.md` and
  `DEFECT_REPORT_TEMPLATE.md` — ship with the practice kit, must stay
  physically inside it.

## Two Independent Product Lines (recap, unchanged since 2026-08-03)

- **V1 — OMS-360 business platform** (`app/`). Live, running code.
- **V2 — AI Customer Support Chatbot** (`docs/business/`,
  `docs/architecture/*-01-...`, `docs/qa/*-01-...`). Fully documented,
  **not built** — status "Documentation Complete, Pending Integration."
- **AI Enterprise Platform / AI Copilot** (`ai/`). Built, 393+ passing
  automated tests, now has partial QA-document coverage via the new
  `Test_Cases.xlsx`/`RTM.xlsx` (previously it had none — see
  `TEST_CASE_COVERAGE.md`'s coverage-asymmetry note, still a valid
  observation even after this pass).
