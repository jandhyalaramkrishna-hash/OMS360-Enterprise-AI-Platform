# PROJECT-WIKI.md — Navigation Index

**Project:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

Start here. This document indexes every permanent project document. All documents below are permanent — never recreated, only updated after every sprint. Paths reflect the enterprise folder structure established 2026-07-19 (DEC-0008); see `docs/governance/MASTER-PROJECT-MEMORY.md` §4 for the full tree.

## Root Files

| Doc | Purpose |
|---|---|
| `README.md` | Project overview, quick navigation, current status |
| `PROJECT_CONTEXT.md` | Session-start context primer — read this first in any new session |
| `VERSION-HISTORY.md` | Semantic version history per sprint/release |

## docs/governance/ — Rules, Memory, Decisions, Risk

| Doc | Purpose |
|---|---|
| `docs/governance/PROJECT-CHARTER.md` | Roles, working rules (1–10), session-start protocol |
| `docs/governance/MASTER-PROJECT-MEMORY.md` | **Single source of truth** — vision, goals, stack, folder structure, architecture, module dependencies, completed/pending sprints, coding/QA/deployment standards, known issues, future roadmap, decision log pointer |
| `docs/governance/MODULE-STATUS.md` | Per-module status tracker (Not Started / In Progress / Complete / Blocked / Documentation Complete – Pending Integration) |
| `docs/governance/DECISION-LOG.md` | Append-only record of every architectural/business/technical decision |
| `docs/governance/DEVELOPMENT-STANDARDS.md` | Mandatory coding standards: Python, FastAPI, React, SQL, Kafka, Docker, PowerShell, documentation |
| `docs/governance/RISK-REGISTER.md` | Project risks, mitigation plans, contingency actions |
| `docs/governance/CHANGE-MANAGEMENT.md` | Granular log of every code/structure modification |

## docs/business/ — Business Requirements & User Stories

| Doc | Purpose |
|---|---|
| `docs/business/BR-01-AI-Customer-Support-Chatbot_v1.1.md` | Business Requirements Document — AI Customer Support Chatbot |
| `docs/business/US-01-AI-Customer-Support-Chatbot_v1.1.md` | User Stories — AI Customer Support Chatbot |

## docs/architecture/ — System & Feature Architecture

| Doc | Purpose |
|---|---|
| `docs/architecture/PROJECT-FOLDER-STANDARD.md` | Proposed internal `backend/` layout — pending reconciliation against the real application baseline |
| `docs/architecture/00_Architecture_Understanding_v1.0.md` | Ground-truth architecture extracted from the external `OMS360_v1.2_Production_Release.zip` (not yet received/verified in this project) |
| `docs/architecture/Feature-01-AI-Customer-Support-Chatbot_v1.1.md` | Full feature spec — AI Customer Support Chatbot (functional flow, prompt design, failure modes, hallucination mitigations) |
| `docs/architecture/FF-01-AI-Customer-Support-Chatbot_v1.1.md` | Functional Flow — AI Customer Support Chatbot |
| `docs/architecture/API-01-AI-Customer-Support-Chatbot_v1.1.md` | API Specification — AI Customer Support Chatbot |
| `docs/architecture/DB-01-AI-Customer-Support-Chatbot_v1.1.md` | Database Design — AI Customer Support Chatbot |
| `docs/architecture/KAFKA-01-AI-Customer-Support-Chatbot_v1.1.md` | Kafka Events — AI Customer Support Chatbot |

## docs/qa/ — QA Standards & AI Chatbot QA Suite

| Doc | Purpose |
|---|---|
| `docs/qa/QA-STANDARDS.md` | Test strategy/levels/naming, API/SQL/logging/performance/security validation, regression & release checklists |
| `docs/qa/TP-01-AI-Customer-Support-Chatbot_v1.1.md` | QA Test Plan — AI Customer Support Chatbot |
| `docs/qa/TC-01-AI-Customer-Support-Chatbot_v1.1.md` | QA Test Cases — AI Customer Support Chatbot |
| `docs/qa/APITEST-01-AI-Customer-Support-Chatbot_v1.1.md` | API Testing — AI Customer Support Chatbot |
| `docs/qa/SQL-01-AI-Customer-Support-Chatbot_v1.1.md` | SQL Validation — AI Customer Support Chatbot |
| `docs/qa/REG-01-AI-Customer-Support-Chatbot_v1.1.md` | Regression Testing — AI Customer Support Chatbot |
| `docs/qa/PERF-01-AI-Customer-Support-Chatbot_v1.1.md` | Performance Testing — AI Customer Support Chatbot |
| `docs/qa/AITEST-01-AI-Customer-Support-Chatbot_v1.1.md` | AI-specific Testing (hallucination guard, prompt regression) — AI Customer Support Chatbot |
| `docs/qa/INTERVIEW-01-AI-Customer-Support-Chatbot_v1.1.md` | Interview Prep Questions — AI Customer Support Chatbot |

## docs/roadmap/ — Phased Delivery Plan

| Doc | Purpose |
|---|---|
| `docs/roadmap/PROJECT-ROADMAP.md` | Phase 1–4 breakdown: objectives, modules, dependencies, deliverables, completion criteria |

## docs/release/ — Sprint & Release Narrative

| Doc | Purpose |
|---|---|
| `docs/release/SPRINT-LOG.md` | Chronological narrative log of each sprint |

## docs/wiki/ — This Document

| Doc | Purpose |
|---|---|
| `docs/wiki/PROJECT-WIKI.md` | This document — navigation index |

## AI Customer Support Chatbot — Status Summary

**Status: Documentation Complete – Pending Integration with OMS360 Production Baseline.** All 16 files are listed above, distributed across `docs/business/`, `docs/architecture/`, and `docs/qa/` by document type (not kept in a single feature-specific folder — this enterprise structure organizes by document *type* across the whole project, consistent with how the governance docs are organized). No source code exists for this feature; it cannot be implemented until `OMS360_v1.2_Production_Release.zip` is provided and verified (see `docs/governance/RISK-REGISTER.md` RISK-005).

**Cross-reference correction:** `Feature-01-AI-Customer-Support-Chatbot_v1.1.md` originally referenced a non-existent filename (`API-01-AI-Chatbot_v1.1.md`). This was corrected during the 2026-07-19 folder reorg to point at the real file, `docs/architecture/API-01-AI-Customer-Support-Chatbot_v1.1.md` (CHG-0003).

Three folders present in the originally uploaded AI Chatbot zip contained no files and were not migrated as documents: Resume Points, Future Enhancements, Diagrams (empty placeholders in the source archive).

## Structure-Only Directories (no documents, reserved for future code)

`backend/`, `frontend/`, `ai/rag/`, `ai/mcp/`, `ai/agents/`, `ai/evals/`, `ai/prompts/`, `database/`, `kafka/`, `docker/`, `monitoring/`, `tests/`, `scripts/`, `release/`, `backups/` — all empty as of this release, per explicit Product Owner instruction not to create placeholder files. See `docs/governance/MASTER-PROJECT-MEMORY.md` §4 for what each is reserved for.

## How These Docs Relate

- **MASTER-PROJECT-MEMORY** is the summary/entry point for project state; it points into the detailed docs rather than duplicating them.
- **DECISION-LOG** captures *why*; **CHANGE-MANAGEMENT** captures *what changed*; **VERSION-HISTORY** captures *when it shipped, as what version*.
- **MODULE-STATUS** (module-level granularity) and **SPRINT-LOG** (sprint-level narrative) feed the "Completed/Pending Sprints" sections of MASTER-PROJECT-MEMORY.
- **DEVELOPMENT-STANDARDS** and **PROJECT-FOLDER-STANDARD** are the binding constraints all code must satisfy (the latter now covers `backend/`'s internal layout specifically — see the note at the top of that document).
- **QA-STANDARDS** defines what "done" means for any module; **RISK-REGISTER** tracks what could stop us from getting there.
- The AI Customer Support Chatbot documentation (business/architecture/qa, listed above) is a frozen, documentation-only Version 2 feature module — it does not represent built code and is not part of the V1 module tracker in `MODULE-STATUS.md`.

## Session Start Protocol (recap)

1. Read root `PROJECT_CONTEXT.md`, then this wiki.
2. Read `docs/governance/MASTER-PROJECT-MEMORY.md` for current state.
3. Check `docs/governance/MODULE-STATUS.md` for what's built vs. pending.
4. Check `docs/governance/DECISION-LOG.md` and `docs/governance/RISK-REGISTER.md` for open items before proceeding.
5. Continue from the last completed sprint — never restart or recreate completed work.

---

*Last updated: 2026-07-19 — Sprint 0 (continued, folder reorg). Documentation baseline plus AI Chatbot documentation module complete, now reorganized under the official enterprise structure. No application code has been written. Awaiting `OMS360_v1.2_Production_Release.zip` before Sprint 1 implementation begins.*
