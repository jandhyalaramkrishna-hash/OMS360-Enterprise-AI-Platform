# PROJECT-ROADMAP.md — OMS-360

Version 1 is broken into four phases. Modules are built respecting the dependency order in `docs/governance/MASTER-PROJECT-MEMORY.md` §6. Phase boundaries may be adjusted only via a logged decision in `docs/governance/DECISION-LOG.md`.

## Phase 1 — Foundation & Core Ordering

**Objectives:** Establish the enterprise folder structure, base FastAPI app, database foundation, and the core customer-facing ordering path (without full event-driven fan-out yet).

**Modules:** Restaurant Management, Menu Management, Customer Order Management (core CRUD + validation), initial Health Monitoring.

**Dependencies:** None (first phase) — establishes the foundation everything else builds on.

**Deliverables:** Scaffolded repo per `docs/architecture/PROJECT-FOLDER-STANDARD.md`; MySQL schema + migrations for restaurants/menus/orders; FastAPI service with `/health`; Swagger docs live; unit + integration tests for these modules; README/API/DB docs updated.

**Completion Criteria:** All Phase 1 modules pass the Release Checklist in `docs/qa/QA-STANDARDS.md`; `docs/governance/MODULE-STATUS.md` shows them Complete; Product Owner sign-off recorded.

## Phase 2 — Event-Driven Backbone & Fulfillment

**Objectives:** Introduce Kafka as the event backbone and connect ordering to inventory, kitchen, and payment workflows, with reliability patterns in place from the start.

**Modules:** Kafka Event Processing, Inventory Management, Kitchen Processing, Payment Processing, Retry & Dead Letter Queue (DLQ), Audit Trail.

**Dependencies:** Phase 1 complete (Customer Order Management must exist and be stable).

**Deliverables:** Kafka topics/producers/consumers per `docs/governance/DEVELOPMENT-STANDARDS.md` §5; idempotent order processing end-to-end; DLQ topics + reprocessing tooling; audit trail persisted for every state transition; integration and E2E tests covering the full order→payment→kitchen flow.

**Completion Criteria:** A simulated order flows through inventory validation, payment, and kitchen prep with correct audit trail entries and no duplicate side effects on replay; Release Checklist passed.

## Phase 3 — Delivery, Notifications & Observability

**Objectives:** Complete the customer-facing lifecycle (delivery + notifications) and build out full operational observability.

**Modules:** Delivery Management, Notification Service, Metrics Monitoring (full), Operations Dashboard, API Documentation (finalized/curated).

**Dependencies:** Phase 2 complete (kitchen "order ready" events must exist to trigger delivery assignment).

**Deliverables:** Delivery assignment workflow; notification events (order confirmed/preparing/out-for-delivery/delivered); `/metrics` fully populated; React-based Operations Dashboard consuming health/metrics/audit data in real time; curated OpenAPI docs published.

**Completion Criteria:** End-to-end order lifecycle observable start-to-finish on the dashboard; Release Checklist passed; performance baselines recorded per `docs/qa/QA-STANDARDS.md` §7.

## Phase 4 — Hardening, Containerization & V1 Stabilization

**Objectives:** Production-hardening pass across all modules; full containerized deployment; close out V1 before any Version 2 (AI/ML) work begins.

**Modules:** Cross-cutting hardening of all 15 V1 modules; Docker/Compose finalization; security/performance validation pass; documentation completeness audit.

**Dependencies:** Phases 1–3 complete.

**Deliverables:** Full `docker-compose.yml` bringing up the entire stack; security validation (§8 of QA Standards) complete; performance baselines confirmed under load; all enterprise docs (this set) fully up to date; `VERSION-HISTORY.md` shows a stable `1.0.0` release.

**Completion Criteria:** All 15 V1 modules marked Complete in `docs/governance/MODULE-STATUS.md`; full regression + release checklist green; Product Owner formally signs off V1 as stable and ready to plan Version 2.

---

## Version 2 (Future — not phased yet)

To be broken into its own phase plan only after V1 reaches `1.0.0` and is formally stabilized, per the Future Roadmap in `docs/governance/MASTER-PROJECT-MEMORY.md` §13.

---

*Last updated: 2026-07-19 — Sprint 0. Phase-to-sprint mapping (which sprint numbers cover which phase) will be appended here as sprints are executed.*
