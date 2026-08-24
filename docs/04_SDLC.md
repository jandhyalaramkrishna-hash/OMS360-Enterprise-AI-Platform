# 04 — Software Development Life Cycle (SDLC)

**Project:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform
**New document, written 2026-08-04** as part of the documentation
reorganization. Synthesized from `docs/governance/PROJECT-CHARTER.md`,
`docs/governance/DEVELOPMENT-STANDARDS.md`, `docs/roadmap/PROJECT-ROADMAP.md`,
`docs/release/SPRINT-LOG.md`, `docs/governance/MODULE-STATUS.md`,
`docs/governance/DECISION-LOG.md`, `docs/governance/CHANGE-MANAGEMENT.md`,
`docs/VERSION-HISTORY.md`, and `README.md`. No process described here is
invented — every rule below already existed in one of those documents;
this file is the first place they're brought together into one
SDLC-shaped narrative.

---

## 1. Project Overview

OMS-360 is an enterprise-grade, event-driven food delivery order
management platform (FastAPI + Apache Kafka + MySQL + Docker), built
alongside a mock-based AI Enterprise Platform (`ai/`) and a fully
documented but unbuilt Version 2 AI Customer Support Chatbot. Full detail:
`docs/01_Project_Overview.md`. This document covers *how* the project is
built and released, not *what* it does.

## 2. Development Methodology

This project follows a **documentation-first, decision-logged, sprint-based**
methodology, formally established in `docs/governance/PROJECT-CHARTER.md`
(the 10 binding working rules) and `docs/governance/DEVELOPMENT-STANDARDS.md`
(the per-technology coding rules: Python/FastAPI/React/SQL/Kafka/Docker/
PowerShell/Documentation). Key characteristics:

- **No code without prior artifact review.** Every sprint starts by
  reading `docs/governance/MODULE-STATUS.md` and `docs/release/SPRINT-LOG.md`
  before writing anything, so completed work is never silently recreated.
- **Every decision is logged, permanently, append-only.** Architectural,
  business, and process decisions go into `docs/governance/DECISION-LOG.md`
  as `DEC-####` entries — never edited or deleted, only superseded.
- **Every change is logged, permanently, append-only.** Concrete
  code/doc/structure changes go into `docs/governance/CHANGE-MANAGEMENT.md`
  as `CHG-####` entries, cross-referenced to the decision(s) behind them.
- **Nothing is marked "Complete" without verification.** External claims
  (e.g., documentation describing a codebase) are not accepted as proof a
  module is built — see §7 below for how this played out in practice.
- **Ask, don't assume.** When information needed to proceed is missing or
  ambiguous, the working rule is to ask the Product Owner rather than
  infer or fabricate.

## 3. SDLC Phases

The project's phased delivery plan is defined in
`docs/roadmap/PROJECT-ROADMAP.md`:

| Phase | Objective | Modules |
|---|---|---|
| **Phase 1 — Foundation & Core Ordering** | Enterprise folder structure, base FastAPI app, database foundation, core ordering path | Restaurant Management, Menu Management, Customer Order Management (core), initial Health Monitoring |
| **Phase 2 — Event-Driven Backbone & Fulfillment** | Kafka as the event backbone; inventory/kitchen/payment workflows with reliability patterns from the start | Kafka Event Processing, Inventory Management, Kitchen Processing, Payment Processing, Retry & DLQ, Audit Trail |
| **Phase 3 — Delivery, Notifications & Observability** | Complete the customer-facing lifecycle; full operational observability | Delivery Management, Notification Service, Metrics Monitoring, Operations Dashboard, API Documentation |
| **Phase 4 — Hardening, Containerization & V1 Stabilization** | Production-hardening pass across all modules; full containerized deployment; close out V1 | Cross-cutting hardening, Docker/Compose finalization, security/performance validation, documentation completeness audit |

Each phase has explicit completion criteria (Release Checklist passed,
`docs/governance/MODULE-STATUS.md` updated, Product Owner sign-off) —
full text in `docs/roadmap/PROJECT-ROADMAP.md`.

## 4. Team Roles

| Role | Owner | Responsibility |
|---|---|---|
| Product Owner / QA Lead | Ram (jandhyala.ramkrishna@gmail.com) | Scope, priorities, sign-off authority on every release checklist, final say on ambiguous decisions |
| Senior Software Engineer (implementation owner) | Claude, acting in this Project | Implementation, documentation upkeep, decision/change logging, QA tooling |

Full role text: `docs/governance/PROJECT-CHARTER.md` §Roles.

## 5. Entry Criteria (per phase / per sprint)

- The prior phase's completion criteria are met and `docs/governance/MODULE-STATUS.md`
  reflects it, **or** the Product Owner has explicitly directed starting
  out of the default dependency order.
- Any external artifact a sprint depends on (e.g., a production baseline
  zip) has been received and — critically — **verified**, not just
  described in documentation. This project's own history has one clear
  example of enforcing this: Sprint 0 discovered its AI Chatbot
  documentation module assumed an already-built `OMS360_v1.2_Production_Release.zip`
  that had not actually been provided or checked, and the Product Owner
  directed all 15 V1 modules stay marked **Not Started** in the tracked
  memory until that baseline was verified in-project (`docs/governance/DECISION-LOG.md`
  DEC-0006, `docs/governance/RISK-REGISTER.md` RISK-005).
- Required prior documentation (BRS/SRS-level requirements for the
  module) exists and has been reviewed.

## 6. Exit Criteria (per phase / per module)

Per `docs/roadmap/PROJECT-ROADMAP.md` and `docs/06_Test_Strategy.md` §12
(Release Checklist; originally distilled from the now-retired
`docs/qa/QA-STANDARDS.md` §10):

- All Regression Checklist items pass (`docs/06_Test_Strategy.md` §11).
- `/health` and `/metrics` verified on all affected services.
- README, API docs, DB docs, and test cases updated for every change.
- `docs/governance/CHANGE-MANAGEMENT.md` updated with the release's changes.
- `docs/VERSION-HISTORY.md` bumped with the correct semantic version.
- `docs/governance/MASTER-PROJECT-MEMORY.md` and `docs/governance/MODULE-STATUS.md`
  updated to reflect current state.
- `docs/governance/DECISION-LOG.md` updated if any decisions were made.
- `docs/governance/RISK-REGISTER.md` reviewed and updated.
- A versioned release ZIP is produced, named exactly
  `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v<version>.zip`.
- Product Owner / QA Lead sign-off recorded in `docs/release/SPRINT-LOG.md`.

## 7. Deliverables

Per phase/sprint: source code for the modules in scope, database schema
and migrations, automated tests, updated API/architecture/DB
documentation, an updated Change Management and Decision Log entry, and a
versioned release artifact. At the project level, this documentation set
(`docs/01`–`19`) plus the governance record (`docs/governance/`,
`docs/roadmap/`, `docs/release/`) are themselves standing deliverables,
kept current every sprint per Working Rule 6.

## 8. Quality Gates

Every module must pass through these gates before being marked Complete
(source: `docs/06_Test_Strategy.md` §1, originally distilled from the
now-retired `docs/qa/QA-STANDARDS.md` §1):

1. **Automated test coverage exists** — unit, integration, API/contract,
   and E2E as applicable — before the module is marked Complete in
   `docs/governance/MODULE-STATUS.md`.
2. **Regression Checklist passes** — see `docs/06_Test_Strategy.md` §11 —
   run via the real Newman + pytest + Allure pipeline
   (`Run_QA_Pipeline.bat` / `jenkins/Jenkinsfile`).
3. **No previously-fixed defect has reappeared** — cross-checked against
   `docs/11_Defect_Report.md`.
4. **Security/logging/performance baselines reviewed** — per
   `docs/06_Test_Strategy.md` §6–8 (with the known, disclosed gaps in
   §10 of that document — no performance/security tooling wired in yet).
5. **Documentation-complete audit** — every module ships with README,
   architecture, API, DB, and test-case coverage before sign-off (Working
   Rule 7 of the Project Charter).

## 9. Release Process

1. Complete the Regression Checklist (`docs/06_Test_Strategy.md` §11) and
   Release Checklist (§12 of the same document / §6 above).
2. Bump `docs/VERSION-HISTORY.md` following the permanent SemVer policy
   (`vMAJOR.MINOR.PATCH`) adopted 2026-07-19.
3. Update `docs/governance/MASTER-PROJECT-MEMORY.md`, `docs/governance/MODULE-STATUS.md`,
   and `docs/governance/DECISION-LOG.md`/`docs/governance/CHANGE-MANAGEMENT.md`
   for whatever changed.
4. Produce a versioned release ZIP:
   `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v<version>.zip`.
5. Record Product Owner / QA Lead sign-off in `docs/release/SPRINT-LOG.md`.

## 10. Current State Against This Process — an Honest Note

This documentation reorganization surfaced a real gap worth recording
rather than glossing over, because Working Rule 9 ("ask instead of
assuming") applies here too:

`docs/VERSION-HISTORY.md` and `README.md` describe the project as having
progressed well past Sprint 0 — the AI Enterprise Platform (`ai/`) is
recorded as **complete at v1.0.0** (393/393 tests passing, Sprints 1–9),
the V1 business platform (`app/`) is recorded as having a **spot-verified
baseline** (referenced as `DEC-0011`), and a real Newman/pytest/Allure/
Jenkins QA pipeline has been built and — as of this session — confirmed
working end-to-end by the Product Owner. `docs/VERSION-HISTORY.md` also
references decision IDs up to `DEC-0022` and a risk `RISK-006`.

However, the more granular governance trackers this project treats as the
source of truth for exactly that information —
`docs/governance/DECISION-LOG.md` (entries stop at `DEC-0010`),
`docs/governance/MODULE-STATUS.md` (still shows all 15 V1 modules **Not
Started**), `docs/governance/RISK-REGISTER.md` (stops at `RISK-005`), and
`docs/release/SPRINT-LOG.md` (entries stop at Sprint 0, 2026-07-19) —
were never updated to add the corresponding `DEC-0011`–`DEC-0022` entries,
`RISK-006`, or the Sprint 1–9 narrative that `docs/VERSION-HISTORY.md`
and `README.md` already assume exist.

This reorganization is scoped to documentation structure only, per
explicit instruction not to touch governance content beyond keeping it in
its own folder — so this note **does not** attempt to backfill those
missing entries (doing so would mean inventing the content of decisions
this session didn't make). It's recorded here so the gap is visible
rather than silently carried forward: the next sprint's exit-criteria pass
should reconcile `docs/governance/DECISION-LOG.md`, `docs/governance/MODULE-STATUS.md`,
`docs/governance/RISK-REGISTER.md`, and `docs/release/SPRINT-LOG.md`
against what `docs/VERSION-HISTORY.md` already claims, per Quality Gate 5
above.
