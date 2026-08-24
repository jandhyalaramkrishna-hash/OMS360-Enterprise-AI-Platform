# docs/ — Documentation Index

**Project:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform
**Reorganized:** 2026-08-04; **final documentation cleanup pass:**
2026-08-04 (same day — retired the remaining `docs/qa/`, `docs/wiki/`,
and `docs/QA_Documents/` folders and the last 15 superseded flat files).
This index replaces `docs/wiki/PROJECT-WIKI.md` as the day-to-day
navigation entry point for QA/SDLC documentation. Start here.

All QA, SDLC, and project process documentation now lives as one flat,
numbered set directly under `docs/`. Governance records (decisions,
change log, risk, sprint narrative, phased roadmap) remain in their own
subfolders — see §3 below for why they weren't flattened in too.

## 1. The Numbered Documentation Set

| # | Document | Covers |
|---|---|---|
| 01 | `01_Project_Overview.md` | What the project is, the three build lines, objectives, tech stack |
| 02 | `02_BRS.md` | Business Requirements Specification |
| 03 | `03_SRS.md` | Software Requirements Specification |
| 04 | `04_SDLC.md` | Development methodology, phases, roles, entry/exit criteria, quality gates, release process |
| 05 | `05_STLC.md` | Requirement analysis → test planning → design → environment → execution → defect reporting → regression → closure |
| 06 | `06_Test_Strategy.md` | How we test and with what — test levels, tooling, standards, regression checklist |
| 07 | `07_Test_Plan.md` | What we test — functional/API/SQL/Kafka/negative/boundary/dashboard/smoke cases (V1, §§1-7), plus the full V2 AI Chatbot test plan (§8) |
| 08 | `08_Test_Cases.md` | Full case-level detail (companion: `Test_Cases.xlsx`) |
| 09 | `09_API_Test_Cases.md` | The real 56-request/168-assertion Newman/Postman suite |
| 10 | `10_RTM.md` | Requirements Traceability Matrix (companion: `RTM.xlsx`) |
| 11 | `11_Defect_Report.md` | Filed defects (all closed) |
| 12 | `12_Test_Summary_Report.md` | What's actually been executed vs. documented-but-not-yet-run |
| 13 | `13_Release_Notes.md` | Reader-facing version history |
| 14 | `14_User_Guide.md` | Quick-start: run the platform, place an order, view dashboards |
| 15 | `15_Installation_Guide.md` | Full technical setup reference, Windows launcher scripts |
| 16 | `16_QA_Automation_Guide.md` | Operational runbook for the QA pipeline scripts |
| 17 | `17_Newman_Setup.md` | Newman/Postman tool-specific setup and troubleshooting |
| 18 | `18_Allure_Setup.md` | Allure tool-specific setup and troubleshooting |
| 19 | `19_Jenkins_Pipeline.md` | Jenkins CI pipeline stage-by-stage reference |

## 2. Companion Spreadsheets (kept, not retired)

`Test_Cases.xlsx` and `RTM.xlsx` remain as companion spreadsheet artifacts
alongside `08_Test_Cases.md` and `10_RTM.md` — same content, different
format (Excel is easier to filter/sort; markdown is easier to read/diff/
link). Neither is the sole source; both are kept in sync by hand when
either changes.

## 3. What's Deliberately Not in This Flat Set

- **`docs/governance/`, `docs/roadmap/`, `docs/release/`** — kept as their
  own folders, per explicit instruction to reserve them for project
  governance records (charter, decision log, change management, risk
  register, module status, master project memory, phased roadmap, sprint
  narrative). These are process/history records, not QA/SDLC deliverables.
- **`docs/business/`, `docs/architecture/`** — the detailed, authoritative
  Version 2 "AI Customer Support Chatbot" specification (9 files: BRD,
  feature spec, user stories, API/DB/Kafka design). `02_BRS.md` and
  `03_SRS.md` summarize and link into these rather than duplicating them.
  This feature is documentation-only (zero lines of code); see
  `01_Project_Overview.md` §2.
- **`docs/qa/` — retired, 2026-08-04 final documentation cleanup.**
  Unlike business/architecture above, this folder's content (V2 test
  plan, SQL validation, AI-specific testing, performance plan,
  regression checklist, interview-prep reference) has been fully
  migrated into the numbered set — `07_Test_Plan.md` §8,
  `08_Test_Cases.md`, `09_API_Test_Cases.md` §2, and
  `06_Test_Strategy.md` §7.1/§11.2 — since it was QA/SDLC deliverable
  content, the exact category this reorganization exists to consolidate
  (unlike business/architecture, which are requirements/design specs,
  not QA documents).
- **Root-level project documents** (`README.md`, `FINAL_RELEASE_REPORT.md`,
  `CLAUDE_CONTEXT.md`, `PROJECT_CONTEXT.md`, `VERSION-HISTORY.md`,
  `RELEASE_VERSION.txt`, `Claude-request.txt`) — left in place; several
  are cited as source material by the numbered set above rather than
  superseded by it.

## 4. Superseded / Retired by This Reorganization

The following are now superseded by the numbered set and should be
removed (see the repo-root cleanup script, since this session's tooling
can write files but not delete them):

- `docs/BRS.md`, `docs/SRS.md`, `docs/Test_Plan.md`, `docs/Test_Strategy.md`,
  `docs/API_Test_Cases.md`, `docs/Defect_Report.md`,
  `docs/Test_Summary_Report.md`, `docs/Release_Notes.md`,
  `docs/User_Guide.md`, `docs/RUN_GUIDE.md`, `docs/NEWMAN_SETUP.md`,
  `docs/ALLURE_SETUP.md`, `docs/JENKINS_PIPELINE.md` — each superseded 1:1
  by its numbered equivalent above.
- `docs/Smoke_Test_Checklist.md`, `docs/Regression_Test_Checklist.md` —
  folded into `07_Test_Plan.md` §6.2 and `06_Test_Strategy.md` §11
  respectively; no longer standalone.
- `docs/wiki/PROJECT-WIKI.md` — functionally superseded by this file. Its
  folder, `docs/wiki/`, is retired.
- `docs/QA_Documents/` — the 2026-08-03 duplicate folder identified in the
  prior consolidation pass; every file in it was either an exact
  duplicate of a `docs/qa/` file (just a header comment added) or a stale
  pre-migration copy of a file already carried forward to `docs/` root —
  nothing in it required fresh migration.
- `docs/qa/` (9 files) — **retired in the 2026-08-04 final documentation
  cleanup pass.** `QA-STANDARDS.md`, `TC-01`, `APITEST-01`, and `REG-01`
  were already fully duplicated in the numbered set; `TP-01`, `SQL-01`,
  `PERF-01`, `AITEST-01`, and `INTERVIEW-01` (genuinely unique content)
  were migrated into `07_Test_Plan.md` §8 and `06_Test_Strategy.md` §7.1
  before this folder's removal — see §3 above.

All of the above are removed by the repo-root cleanup script
(`Cleanup_Reorganized_Docs.bat`), since this session's tooling can write
files but not delete them.

`docs/QA_DOCUMENT_INVENTORY.md`, `docs/TEST_CASE_COVERAGE.md`,
`docs/PLAYWRIGHT_EXECUTION_REPORT.md`, and `docs/TC-GAP-01-Missing-Coverage.md`
remain in place as historical/source records referenced by the numbered
set (e.g. `08_Test_Cases.md`'s Coverage Summary, `07_Test_Plan.md` §6).

## 5. Where Governance Lives

| Folder | Purpose |
|---|---|
| `docs/governance/` | Project Charter, Master Project Memory, Decision Log, Development Standards, Module Status, Risk Register, Change Management |
| `docs/roadmap/` | Phase 1–4 delivery plan |
| `docs/release/` | Sprint-by-sprint narrative log |

See `04_SDLC.md` §9 for how this documentation set and the governance
record relate, and §10 for an honest note on a gap this reorganization
surfaced between what `docs/VERSION-HISTORY.md` claims and what the
granular governance trackers currently show.

## 6. Session-Start Reading Order (unchanged in spirit from the former wiki)

1. `docs/PROJECT_CONTEXT.md` — session-start primer.
2. `docs/governance/MASTER-PROJECT-MEMORY.md` — governance source of truth.
3. This file — QA/SDLC documentation index.
4. `01_Project_Overview.md` → work through the numbered set as needed.
