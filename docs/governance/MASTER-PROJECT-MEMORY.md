# MASTER-PROJECT-MEMORY.md — OMS-360 Enterprise Food Delivery Platform

**Official Project Name (as of 2026-07-19, DEC-0008):** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

**This is the single source of truth for the entire project.** Every session must read this document first (or start from root `PROJECT_CONTEXT.md`, which points here). It is permanent and is never recreated — only updated, after every sprint, per `docs/governance/CHANGE-MANAGEMENT.md`.

Related permanent docs: see `docs/wiki/PROJECT-WIKI.md` for the full navigation index, or root `README.md` for a high-level project overview.

---

## 1. Project Vision

OMS-360 is a production-style, enterprise-grade, event-driven food ordering and delivery management system that automates the complete order lifecycle — from customer order placement to successful delivery — while demonstrating how modern distributed systems process high volumes of orders reliably and efficiently. It is built to a production standard, not a demo standard: reliability, traceability, and operability are first-class requirements alongside functionality.

## 2. Business Goals

- Deliver an end-to-end online food ordering platform covering customers, restaurants, kitchens, inventory, payments, delivery, and operations staff.
- Process orders reliably at scale using event-driven architecture (Apache Kafka) rather than tightly-coupled synchronous calls.
- Guarantee no order is lost, duplicated, or silently dropped (idempotency, retries, DLQ).
- Give the business full traceability of every order (audit trail) and full operational visibility (health, metrics, dashboards).
- Establish a modular architecture that can absorb Version 2 AI/ML and geolocation capabilities without a rewrite.

## 3. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend API | FastAPI (Python) | REST APIs, async-first |
| Messaging / Events | Apache Kafka | Order lifecycle events, retry topics, DLQ topics |
| Database | MySQL | Transactional store of record |
| Containerization | Docker (+ Docker Compose) | Local and deployment packaging |
| Frontend (Operations Dashboard) | React (originally planned, DEC-0002) — **unconfirmed against real system; see §12** | Real-time operational dashboards |
| Tooling / Ops scripting | PowerShell | Windows-side dev/ops scripts (per Product Owner environment) |
| API Docs | Swagger / OpenAPI (via FastAPI) | Auto-generated + curated |

Stack decisions are binding; changes must go through `docs/governance/DECISION-LOG.md`.

## 4. Folder Structure

**This is the authoritative, current top-level structure**, established 2026-07-19 (DEC-0008), containing all documentation produced to date plus structure-only directories reserved for future code (no placeholder files inside them, per Product Owner instruction):

```
Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform/
│
├── docs/
│   ├── architecture/     # Architecture Understanding, Feature/API/DB/Kafka specs, folder standard
│   ├── business/         # Business Requirements, User Stories
│   ├── governance/       # Charter, Master Memory, Decision Log, Dev Standards, Module Status, Risk Register, Change Management
│   ├── qa/                # QA Standards + full AI Chatbot QA suite (test plan/cases, API/SQL/regression/performance/AI testing, interview prep)
│   ├── roadmap/           # Phase 1–4 roadmap
│   ├── release/           # Sprint log (release/sprint narrative history)
│   └── wiki/              # Navigation index (PROJECT-WIKI.md)
│
├── backend/               # (empty — reserved for the FastAPI application once the baseline arrives)
├── frontend/              # (empty — reserved for the Operations Dashboard frontend)
├── ai/
│   ├── rag/                # (empty — reserved for AI Chatbot retrieval/RAG implementation)
│   ├── mcp/                # (empty — reserved for MCP tool integrations)
│   ├── agents/              # (empty — reserved for agent orchestration code)
│   ├── evals/                # (empty — reserved for AI feature evaluation harnesses)
│   └── prompts/               # (empty — reserved for versioned system prompts, e.g. the AI Chatbot system prompt in docs/architecture/Feature-01...)
│
├── database/              # (empty — reserved for schema/migrations once the baseline arrives)
├── kafka/                 # (empty — reserved for topic/schema definitions)
├── docker/                # (empty — reserved for Dockerfiles / docker-compose)
├── monitoring/             # (empty — reserved for health/metrics/observability config)
├── tests/                  # (empty — reserved for the test suite, per docs/qa/QA-STANDARDS.md)
├── scripts/                 # (empty — reserved for PowerShell/ops scripts)
├── release/                 # (empty — reserved for built release archives)
├── backups/                  # (empty — reserved for project backups)
│
├── README.md               # project overview and navigation
├── PROJECT_CONTEXT.md       # session-start context primer
└── VERSION-HISTORY.md       # semantic version history
```

No module may deviate from this top-level structure without a logged decision in `docs/governance/DECISION-LOG.md`. The internal layout of `backend/` (and, by extension, `frontend/`, `database/`, `kafka/`, `docker/`) is proposed in `docs/architecture/PROJECT-FOLDER-STANDARD.md` but not yet finalized — it must be reconciled against the real `OMS360_v1.2_Production_Release.zip` layout once received (§8, §12).

## 5. Architecture Overview

- **Style:** Event-driven modular architecture (FastAPI service) communicating via Kafka topics for cross-module workflows (order → inventory → kitchen → payment → delivery → notification), with synchronous REST for client-facing and query operations.
- **Reliability patterns:** idempotent order processing (idempotency keys), retry with backoff, Dead Letter Queue (DLQ) for poison messages, structured logging, centralized exception handling, audit trail table(s), health (`/health`) and metrics (`/metrics`) endpoints.
- **Data of record:** MySQL, accessed via a transactional data-access layer; Kafka events are the integration/eventing layer, not the source of truth for state.
- **Observability:** structured logs, health checks, metrics endpoints, and an operations dashboard consuming those signals.
- Detailed diagrams/ADRs to be added here once the verified application baseline is available (§12).

## 6. Module Dependencies

High-level dependency direction (upstream → downstream):

1. Restaurant Management → Menu Management (a restaurant owns its menu)
2. Menu Management → Customer Order Management (orders reference menu items)
3. Customer Order Management → Inventory Management (stock validation/decrement)
4. Customer Order Management → Kafka Event Processing (order events published)
5. Kafka Event Processing → Kitchen Processing (order accepted → prep)
6. Kafka Event Processing → Payment Processing (payment events)
7. Kitchen Processing → Delivery Management (order ready → assign delivery)
8. Delivery Management → Notification Service (status updates to customer)
9. All modules → Audit Trail (every state change is logged)
10. All modules → Health Monitoring / Metrics Monitoring (operational signals)
11. Retry & DLQ is cross-cutting — wraps all Kafka consumers
12. Operations Dashboard consumes Health, Metrics, Audit Trail, and module states
13. API Documentation is cross-cutting — generated from all REST modules

This dependency order is the default build sequence for phases in `docs/roadmap/PROJECT-ROADMAP.md`, unless the Product Owner directs otherwise.

## 7. Completed Sprints

- **Sprint 0 — Project Kickoff & Enterprise Documentation Baseline** (2026-07-19): Project charter, roles, rules, and the full enterprise documentation set established. No application code written.
- **Sprint 0 (continued) — AI Customer Support Chatbot documentation module** (2026-07-19): Imported and froze a 16-file documentation package (BRD, Architecture, Feature Spec, User Stories, Functional Flow, API/DB/Kafka specs, full QA suite) for a Version 2 "AI Customer Support Chatbot" feature. Status: **Documentation Complete – Pending Integration with OMS360 Production Baseline.** No source code created or inferred.
- **Sprint 0 (continued) — Official project name adopted; enterprise folder reorg; Sprint 0 frozen** (2026-07-19): Adopted the official project name and reorganized all 29 documents into the structure described in §4. Sprint 0 is now formally frozen.

(Full history in `docs/release/SPRINT-LOG.md` and `VERSION-HISTORY.md`.)

## 8. Pending Sprints

- **Sprint 1** — blocked pending receipt and verification of `OMS360_v1.2_Production_Release.zip`, which the Product Owner has designated as the official V1 application baseline (DEC-0006). No code will be scaffolded, inferred, or written before it arrives.
- All 15 Version 1 modules remain **Not Started** in this project's verified memory (see §12 and `docs/governance/MODULE-STATUS.md`) — external documentation describing that codebase is not treated as proof it is built/complete here.
- Once the baseline is received: verify it, reconcile `docs/architecture/PROJECT-FOLDER-STANDARD.md` and this document's Tech Stack (§3) and Architecture (§5) sections against the real code, update `docs/governance/MODULE-STATUS.md` accordingly, then integrate the frozen AI Chatbot documentation module as real Sprint 1+ implementation work.

## 9. Coding Standards

Full detail in `docs/governance/DEVELOPMENT-STANDARDS.md`. Summary: PEP8 + type hints for Python/FastAPI, structured logging everywhere, no bare excepts, idempotency on all write endpoints that matter, SQL via parameterized queries/ORM only, Kafka consumers must be idempotent and DLQ-aware, Docker images must be minimal and reproducible, dashboard frontend code follows standard enterprise conventions (typed, tested, no inline business logic in views) — framework choice to be reconciled against the real codebase once received (§12).

## 10. QA Standards

Full detail in `docs/qa/QA-STANDARDS.md`. Summary: unit + integration + contract + E2E test levels required, standardized test naming, API/SQL/logging/performance/security validation required per module, regression checklist and release checklist mandatory before any sprint is marked Complete.

## 10a. Versioning & Release Standard (permanent, DEC-0010)

Strict Semantic Versioning (`vMAJOR.MINOR.PATCH`) for every release, effective 2026-07-19. Every completed sprint must update `VERSION-HISTORY.md`, this document, and `docs/wiki/PROJECT-WIKI.md` (if the doc set changed), then produce a release ZIP named exactly `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v<version>.zip`. Full policy and rationale: `VERSION-HISTORY.md` (top section) and `docs/governance/DECISION-LOG.md` DEC-0010. This release (`v0.1.0`) is the first to follow the standard.

## 11. Deployment Standards

- All services must be containerized (Docker) with a documented `Dockerfile` and `docker-compose.yml` for local/integration environments.
- No secrets committed to source; environment-based configuration only.
- Every deployable module must expose `/health` and `/metrics` before it can be considered deployment-ready.
- Database schema changes must ship with migrations, never manual ad-hoc DDL.
- Deployment steps and environment requirements are documented per module in that module's README as it is built.
- Full checklist maintained in `docs/qa/QA-STANDARDS.md` (Release Checklist) and referenced here.

## 12. Known Issues

- **Unverified application baseline (Open, raised 2026-07-19):** Documentation received this sprint (`docs/architecture/00_Architecture_Understanding_v1.0.md`) describes an already-built production codebase, `OMS360_v1.2_Production_Release.zip`, implementing most V1 modules (FastAPI + SQLAlchemy 2.0 + MySQL + Kafka + two static HTML/JS dashboards, no auth layer). That codebase has not been provided to or verified in this project. Until it arrives, this project's own record (`docs/governance/MODULE-STATUS.md`) keeps all 15 V1 modules as Not Started. See `docs/governance/RISK-REGISTER.md` RISK-005 and `docs/governance/DECISION-LOG.md` DEC-0006.
- **Stack detail conflict (Open, raised 2026-07-19):** DEC-0002 recorded React as the intended dashboard frontend; the external architecture reference instead describes the existing dashboards as static HTML + vanilla JS with 6-second polling. Not reconciled until the real codebase is verified (see DEC-0002's superseded note).
- **Pre-existing broken cross-reference in AI Chatbot docs (RESOLVED 2026-07-19):** `docs/architecture/Feature-01-AI-Customer-Support-Chatbot_v1.1.md` previously referenced a file named `API-01-AI-Chatbot_v1.1.md`, which never existed. Corrected during the Sprint 0 folder reorg (CHG-0003) to point at the actual file, `docs/architecture/API-01-AI-Customer-Support-Chatbot_v1.1.md`.

## 13. Future Roadmap

Version 2 (post-V1 stabilization): AI-powered Order Validation, AI Fraud Detection, Predictive Inventory Management, AI Delivery ETA Prediction, AI Root Cause Analysis, Live GPS Delivery Tracking, Geofencing, Route Optimization, AI Chat Assistant, Natural Language to SQL, Predictive Business Analytics, Intelligent Dashboard Insights. Detailed phase breakdown in `docs/roadmap/PROJECT-ROADMAP.md`. The **AI Customer Support Chatbot** (mapped to "AI Chat Assistant") now has a complete, frozen design (`docs/architecture/`, `docs/business/`, `docs/qa/` — see `docs/wiki/PROJECT-WIKI.md` for the full file list) ready to build as soon as V1 is stabilized and the real codebase is verified — this is ahead of the rest of the V2 backlog, which remains unspecified. The `ai/{rag,mcp,agents,evals,prompts}/` structure (§4) is reserved for this feature's eventual implementation.

## 14. Decision Log

Full append-only log in `docs/governance/DECISION-LOG.md`. This section is a pointer only — do not duplicate entries here. Most recent entries: DEC-0008, DEC-0009, DEC-0010 (2026-07-19) — official project name adopted, enterprise folder structure established, version-history disambiguation, permanent SemVer + release-naming policy adopted.

---

*Last updated: 2026-07-19 — Sprint 0 (continued, folder reorg). This document, along with the rest of the Sprint 0 documentation set, is now frozen as the official Sprint 0 release under the name Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform. Next update occurs at the start of Sprint 1, once `OMS360_v1.2_Production_Release.zip` is received.*
