# RISK-REGISTER.md — OMS-360

Maintain every project risk here with mitigation and contingency plans. Review and update at the end of every sprint (Release Checklist item in `docs/qa/QA-STANDARDS.md`). Never delete a risk — close it out with a status change and date instead.

Format per entry: ID, Description, Category, Likelihood, Impact, Mitigation, Contingency, Status, Date Raised, Date Closed (if applicable).

---

### RISK-001 — Kafka event ordering/duplication under retry
- Category: Technical / Reliability
- Likelihood: Medium
- Impact: High (could cause duplicate charges, duplicate orders, or out-of-order state transitions)
- Mitigation: Enforce idempotency keys on all order-mutating operations; use message keys for correct partitioning; consumers designed to be idempotent per `docs/governance/DEVELOPMENT-STANDARDS.md` §5.
- Contingency: DLQ + manual reprocessing tooling; audit trail allows reconstructing true order state if an inconsistency occurs.
- Status: Open (design-stage mitigation planned for Phase 2)
- Date Raised: 2026-07-19

### RISK-002 — Undefined authentication/authorization mechanism
- Category: Security
- Likelihood: High (currently undefined)
- Impact: High (customer, restaurant, and internal ops endpoints all need distinct access control)
- Mitigation: AuthN/AuthZ approach must be explicitly decided and logged in `docs/governance/DECISION-LOG.md` before any customer- or restaurant-facing endpoint ships.
- Contingency: Endpoints remain internal/non-deployed until auth is defined; no production exposure without it.
- Status: Open. **Update 2026-07-19:** external architecture reference received this sprint (see RISK-005) states the real system currently has **no auth implemented at all** ("no login, no JWT, no RBAC") — consistent with this risk being unresolved, not a new development.
- Date Raised: 2026-07-19

### RISK-003 — Scope creep from Version 2 (AI/ML/GPS) features into V1
- Category: Business / Schedule
- Likelihood: Medium
- Impact: Medium (delays V1 stabilization)
- Mitigation: Version 2 features are explicitly out of scope until V1 reaches `1.0.0` per `docs/roadmap/PROJECT-ROADMAP.md`; any V2 work request mid-V1 requires an explicit Product Owner decision logged in `docs/governance/DECISION-LOG.md`.
- Contingency: Roadmap re-sequencing if Product Owner reprioritizes; documented, not silent.
- Status: Open (monitoring). **Update 2026-07-19:** AI Customer Support Chatbot (V2) documentation was received and frozen as documentation-only (DEC-0005) — no implementation occurred, so this risk has not materialized, but it is now closer: the design is complete and "pending build approval" per the source docs. Continue to hold the line at Phase 4/V1 `1.0.0` before any AI build starts.
- Date Raised: 2026-07-19

### RISK-004 — Folder structure / repo location not yet finalized
- Category: Process
- Likelihood: Medium (top-level structure now resolved; internal backend/ layout still open)
- Impact: Low-Medium (rework if changed after code exists)
- Mitigation: Repo location and folder structure confirmed before any code is written (Sprint 1 kickoff blocker per `docs/architecture/PROJECT-FOLDER-STANDARD.md`).
- Contingency: If changed after Sprint 1 starts, a migration decision is logged and folder standard updated accordingly.
- Status: **Partially Resolved 2026-07-19** — the official top-level enterprise folder structure is now established (Product Owner directive: `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform/` with `docs/`, `backend/`, `frontend/`, `ai/`, `database/`, `kafka/`, `docker/`, `monitoring/`, `tests/`, `scripts/`, `release/`, `backups/` — see DEC-0008). Still open: the internal layout of `backend/` proposed in `docs/architecture/PROJECT-FOLDER-STANDARD.md` (`app/api/v1/...`) has not been reconciled against the real `OMS360_v1.2_Production_Release.zip` layout (per the received architecture doc: `app/routes`, `app/services`, `app/messaging`, `app/static`, `migrations/`) — see RISK-005.
- Date Raised: 2026-07-19

### RISK-005 — Project execution blocked pending the OMS360_v1.2_Production_Release.zip application baseline
- Category: Process / Dependency
- Likelihood: Certain (confirmed blocker as of 2026-07-19)
- Impact: High — no application code, integration, or Sprint 1 implementation work of any kind can proceed without it (per explicit Product Owner instruction: no scaffolding, no placeholder code, no inferred source).
- Mitigation: None needed beyond waiting — this is an intentional, Product-Owner-directed hold, not an accidental gap. All documentation work (this project's governance docs, plus the AI Chatbot doc module) continues in the meantime.
- Contingency: On receipt, the codebase must be verified (checksums, structure review) before `docs/governance/MODULE-STATUS.md` is updated to reflect any module as built, per `docs/governance/PROJECT-CHARTER.md` Rule 4.
- Status: Open
- Date Raised: 2026-07-19

---

*Last reviewed: 2026-07-19 — Sprint 0 (continued, folder reorg).*
