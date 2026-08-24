<!-- Migrated from docs/QA_Documents/TC-GAP-01-Missing-Coverage.md to docs/ root on 2026-08-04, as part of retiring the QA_Documents/ duplicate folder. Content unchanged. Now also reflected in docs/Test_Cases.xlsx ("V1 Boundary" / "V1 Dashboard" sheets) and docs/Smoke_Test_Checklist.md. -->

# TC-GAP-01 — Missing Test Case Coverage (originally written 2026-08-03)

**Purpose:** reviewing every existing test case before writing anything
new, and creating only what's genuinely missing — not duplicating
`docs/Test_Plan.md`, `docs/qa/TC-01-...`, or
`Student_Practice_Kit/docs/TEST_CASES.md`. This document contains **only**
cases that were not already covered anywhere in the repository. It does
not restate FUNC/API/NEG/ORD/LIC/SYS/TC cases that already exist — see
`docs/TEST_CASE_COVERAGE.md` for where those live.

Three categories were requested by name and had no dedicated home
anywhere in the repo: **Boundary Value**, **Smoke**, and **Dashboard**
test cases. They're written below, grounded strictly in behavior already
documented elsewhere in this repo (`docs/Test_Plan.md`, `docs/RUN_GUIDE.md`,
`docs/release/SPRINT-LOG.md`, `Student_Practice_Kit/docs/API_GUIDE.md`) —
nothing here asserts a business rule that isn't already written down
somewhere else in the project.

---

## 1. Boundary Value Test Cases (V1 platform)

Existing test cases assert *that* validation happens (`docs/Test_Plan.md`
NEG-01/02, `ORD-NEG-01/02` in the Student kit); none of them assert the
exact **boundary**. These do. Full table:
`docs/Test_Cases.xlsx`, sheet "V1 Boundary" (BND-01..07).

## 2. Smoke Test Suite (V1 platform + AI platform)

No document anywhere names a specific "smoke suite." This is a **curated
subset of existing cases** — not new content — selected as the minimum
set that proves the whole stack is alive after any deploy. Now formalized
as an actual checklist: `docs/Smoke_Test_Checklist.md`.

## 3. Dashboard Test Cases (all four dashboards — genuinely missing)

`verification/screenshots/` only covers Operations and Monitoring,
captured before the Inventory Dashboard (DEC-0031) and AI Copilot
Dashboard (DEC-0033) existed, and it's evidence from a manual pass, not a
repeatable test-case document. These give the four dashboards their
first-ever written test coverage. Full table: `docs/Test_Cases.xlsx`,
sheet "V1 Dashboard" (DASH-01..06).

**Note on scope:** these six cases are not exhaustive — a full dashboard
test pass would also need every card/widget enumerated per dashboard,
which requires reading each dashboard's actual HTML/JS
(`app/static/*.html`) rather than relying on the sprint narrative alone.
That deeper pass is recommended as follow-up work.

## 4. What was deliberately NOT written here, and why

This document stops short of inventing test cases for **Restaurant
Management, Menu Management, Kitchen Processing (as its own module),
Payment Processing, Delivery Management, Notification Service, Audit
Trail, or Retry/DLQ handling** as standalone suites. Each of these appears
only as an embedded step inside `docs/Test_Plan.md`'s order-lifecycle
cases (FUNC-03/04, KAFKA-01…05) — real coverage exists for the
order-lifecycle *path* through these modules, but not for each module's
own edge cases. Writing accurate test cases for those would require
reading the actual route/service code under `app/routes/`/`app/services/`
for each module first — this gap is recorded explicitly in
`docs/TEST_CASE_COVERAGE.md` and `docs/RTM.xlsx` as a GAP rather than
guessed at here.
