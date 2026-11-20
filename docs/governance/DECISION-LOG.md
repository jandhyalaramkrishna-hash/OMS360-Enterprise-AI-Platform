# DECISION-LOG.md — OMS-360

Append-only. **Never remove or rewrite previous entries** — if a decision is later reversed, add a new entry that supersedes it and references the original entry's ID. Every entry must include Date, Sprint, Decision, Reason, Alternatives Considered (if any), and Status.

Format:

```
### DEC-XXXX — <short title>
- Date:
- Sprint:
- Decision:
- Reason:
- Alternatives Considered:
- Status: Active | Superseded by DEC-YYYY
```

---

### DEC-0001 — Adopt FastAPI + Kafka + MySQL + Docker as the core stack
- Date: 2026-07-19
- Sprint: Sprint 0
- Decision: OMS-360 will be built on FastAPI (backend REST), Apache Kafka (event backbone), MySQL (system of record), and Docker (containerization), as originally scoped in the project description.
- Reason: Matches the stated project goals (event-driven architecture, scalable REST APIs, reliable async processing) and is a widely-supported, production-proven combination.
- Alternatives Considered: None formally evaluated — stack was specified at project inception by the Product Owner.
- Status: Active

### DEC-0002 — React selected for the Operations Dashboard frontend
- Date: 2026-07-19
- Sprint: Sprint 0
- Decision: The Operations Dashboard module's frontend will be built in React.
- Reason: Product Owner requested React-specific coding standards, implying React as the dashboard framework; React is well-suited to real-time, component-driven operational UIs.
- Alternatives Considered: None formally evaluated at this stage.
- Status: **Superseded by DEC-0006** — external architecture reference (received 2026-07-19, see DEC-0006) describes the actual existing dashboards as static HTML + vanilla JS, not React. Kept here unmodified per append-only rule; do not delete. Resolution pending arrival/verification of the real codebase.

### DEC-0003 — Full enterprise documentation set established before Sprint 1
- Date: 2026-07-19
- Sprint: Sprint 0
- Decision: Ten permanent enterprise documents (MASTER-PROJECT-MEMORY, DECISION-LOG, DEVELOPMENT-STANDARDS, QA-STANDARDS, PROJECT-ROADMAP, PROJECT-FOLDER-STANDARD, RISK-REGISTER, CHANGE-MANAGEMENT, VERSION-HISTORY, PROJECT-WIKI) are created and must be complete before any application code is written.
- Reason: Product Owner mandated documentation-first process to guarantee project memory, traceability, and enterprise-grade discipline across all future sprints.
- Alternatives Considered: Lighter-weight docs-as-you-go approach — rejected per explicit Product Owner instruction.
- Status: Active

### DEC-0004 — Original Sprint 0 docs (PROJECT-CHARTER, MODULE-STATUS, SPRINT-LOG) retained alongside the new enterprise doc set
- Date: 2026-07-19
- Sprint: Sprint 0
- Decision: `docs/governance/PROJECT-CHARTER.md`, `docs/governance/MODULE-STATUS.md`, and `docs/release/SPRINT-LOG.md` (created earlier in Sprint 0) are kept as-is. `docs/governance/MASTER-PROJECT-MEMORY.md` is now the single source of truth and supersedes them for status/summary purposes; `MODULE-STATUS.md` and `SPRINT-LOG.md` remain the detailed trackers referenced by it.
- Reason: Avoid data loss / duplication conflicts; Product Owner rule states these enterprise docs must never be recreated, and did not direct deletion of prior docs.
- Alternatives Considered: Merge and delete originals — deferred; can be done later with explicit Product Owner approval if desired.
- Status: Active

### DEC-0005 — AI Customer Support Chatbot documentation imported as a frozen, documentation-only module
- Date: 2026-07-19
- Sprint: Sprint 0 (continued)
- Decision: The uploaded 16-file documentation package for the "AI Customer Support Chatbot" (Business Requirements, Architecture, Feature spec, API/DB/Kafka specs, full QA suite) is stored permanently under `ai-chatbot/` in this Project and its status is recorded as **"Documentation Complete – Pending Integration with OMS360 Production Baseline."** No source code was generated, inferred, or scaffolded for it.
- Reason: Explicit Product Owner instruction: freeze the AI documentation module as complete, do not recreate/infer missing application source code, do not scaffold placeholder code, do not invent project files.
- Alternatives Considered: Marking it "In Progress" or attempting a partial implementation — rejected; Product Owner was explicit that no code work happens until the production baseline arrives.
- Status: Active

### DEC-0006 — OMS360_v1.2_Production_Release.zip designated as the official application baseline (not yet received)
- Date: 2026-07-19
- Sprint: Sprint 0 (continued)
- Decision: The application source code referenced throughout the AI Chatbot documentation (`OMS360_v1.2_Production_Release.zip` — FastAPI + SQLAlchemy 2.0 + MySQL + Kafka + static HTML/JS dashboards, per the uploaded `Architecture/00_Architecture_Understanding_v1.0.md`) is designated the official V1 application baseline for this project going forward. Product Owner confirmed it will be provided separately. Until it is received and verified in this project, `docs/governance/MODULE-STATUS.md` continues to show all 15 V1 modules as **Not Started** — this project does not take the existence or completeness of that codebase on faith from documentation alone.
- Reason: Enterprise standard of verifying artifacts before recording them as done (Rule 4 of `docs/governance/PROJECT-CHARTER.md`); explicit Product Owner instruction not to assume or infer missing source code.
- Alternatives Considered: Immediately marking V1 modules Complete based on the architecture document's description — rejected as unverified and against project rules.
- Status: Active — open until baseline zip is received and verified.

### DEC-0007 — Release package filename vs. internal semantic version
- Date: 2026-07-19
- Sprint: Sprint 0 (continued)
- Decision: The Product Owner requested a release artifact named exactly `OMS360_AI_Enterprise_v0.1.0.zip`. Because `VERSION-HISTORY.md` already used tag `v0.1.0` for the Sprint 0 governance-documentation baseline, this release is logged internally as semantic version **v0.2.0** in `VERSION-HISTORY.md` to avoid two different releases sharing one version tag. The delivered zip file itself is named exactly as the Product Owner requested (`OMS360_AI_Enterprise_v0.1.0.zip`) — the filename and the internal semver tag are intentionally decoupled and both are recorded for traceability.
- Reason: Preserve accurate, non-colliding version history while still honoring the Product Owner's literal naming instruction.
- Alternatives Considered: Renaming the deliverable to `..._v0.2.0.zip` — rejected in favor of following the literal instruction; Overwriting the existing v0.1.0 entry — rejected, violates append-only versioning.
- Status: Active

### DEC-0008 — Official project name adopted and enterprise folder structure established
- Date: 2026-07-19
- Sprint: Sprint 0 (continued — folder reorg)
- Decision: The official project name is designated **"Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform."** All 29 existing documents (13 governance docs + 16 AI Chatbot documentation-module docs) are reorganized into a standard enterprise folder structure: `docs/{architecture,business,governance,qa,roadmap,release,wiki}` for documentation, plus structure-only (no placeholder files) top-level directories for future code: `backend/`, `frontend/`, `ai/{rag,mcp,agents,evals,prompts}`, `database/`, `kafka/`, `docker/`, `monitoring/`, `tests/`, `scripts/`, `release/`, `backups/`. Two new root files are introduced: `README.md` (project overview/navigation) and `PROJECT_CONTEXT.md` (session-start context primer). `VERSION-HISTORY.md` moves to the project root.
- Reason: Explicit Product Owner instruction to freeze Sprint 0 under the official project identity and a scalable enterprise repository structure before Sprint 1 begins, so future backend/frontend/AI/infra code has a defined home from day one.
- Alternatives Considered: Keeping the flat `claude/` + `ai-chatbot/` layout — rejected as it doesn't scale to a full enterprise repo with application code, infra, and AI-specific subsystems (RAG, MCP, agents, evals, prompts).
- Status: Active

### DEC-0009 — This folder-reorg release recorded as VERSION-HISTORY.md `v0.1.0` (Official Project Structure Baseline), alongside the pre-existing `v0.1.0`/`v0.2.0` entries
- Date: 2026-07-19
- Sprint: Sprint 0 (continued — folder reorg)
- Decision: Per explicit, literal Product Owner instruction ("record this as Version v0.1.0"), this reorg is logged in `VERSION-HISTORY.md` as a new entry titled **"v0.1.0 — Official Project Structure Baseline."** This creates a second `v0.1.0`-labeled entry alongside the original Sprint 0 governance-documentation baseline (also tagged `v0.1.0`) and the AI Chatbot import (`v0.2.0`). All three entries are retained in full per the append-only rule — none were deleted or rewritten. The new entry is explicitly labeled to disambiguate it as the official-name/official-structure milestone rather than silently colliding with the earlier tag.
- Reason: Honor the Product Owner's literal instruction while preserving complete, honest version history — silently overwriting or renumbering the earlier `v0.1.0` entry would violate the append-only rule in `VERSION-HISTORY.md` and `docs/governance/PROJECT-CHARTER.md` Rule 1 (complete project memory).
- Alternatives Considered: Using `v0.3.0` to keep one strictly linear sequence — not chosen because the Product Owner explicitly directed `v0.1.0`; recorded here as the reasonable alternative if the Product Owner later wants to switch to strict linear semver.
- Status: Active

### DEC-0010 — Semantic Versioning and release ZIP naming convention adopted as a permanent standard
- Date: 2026-07-19
- Sprint: Sprint 0 (continued — frozen before Sprint 1)
- Decision: The project adopts strict **Semantic Versioning (SemVer)** — format `vMAJOR.MINOR.PATCH` (e.g., `v0.1.0`, `v0.2.0`, `v1.0.0`, `v1.1.0`, `v2.0.0`) — for all future releases, permanently, effective immediately. Every completed sprint must, at minimum: update `VERSION-HISTORY.md`, update `docs/governance/MASTER-PROJECT-MEMORY.md`, update `docs/wiki/PROJECT-WIKI.md` (if the doc set changed), and produce a versioned release ZIP. Release ZIPs are named **`Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v<version>.zip`** (e.g., `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v0.1.0.zip`). This is a permanent standard, binding for all future sprints unless explicitly changed by the Product Owner.
- Reason: Explicit Product Owner directive, given before Sprint 1 begins, to end the ad-hoc release naming used during Sprint 0 (see DEC-0007, DEC-0009) and establish one unambiguous, predictable convention going forward. This release (Sprint 0's frozen documentation baseline) is the first to use the new convention: the zip filename `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v0.1.0.zip` now matches its `VERSION-HISTORY.md` version tag exactly, resolving the filename/version-tag decoupling that DEC-0007 and DEC-0009 had to work around.
- Alternatives Considered: Continuing with the `OMS360_AI_Enterprise_v<x>.zip` naming used for the two earlier Sprint 0 deliverables — superseded, not reused, per explicit instruction.
- Status: Active — permanent standard.

---

*Open item: DEC-pending — choice of first module for Sprint 1 and repo location (already resolved at the top level by DEC-0008; still open: internal `backend/` layout, and the first module to implement) — superseded in practice by the pending arrival of `OMS360_v1.2_Production_Release.zip` (DEC-0006), which will likely determine both. Will be logged as DEC-0011 once resolved.*

### DEC-0034 — Low-stock email fix: deploy by image rebuild; live test via one-off single-alert script
- Date: 2026-11-20
- Sprint: Maintenance — Low-Stock Email Notification Fix (DEF-006)
- Decision: (1) Deploy the fix by rebuilding the `oms360-engine` / `oms360-consumer` images; keep the existing single-stage Dockerfile that bakes `tests/` and pytest into the image. (2) Perform the controlled live Gmail test with `scripts/dispatch_single_alert.py`, piped into the running container, which calls the existing `inventory_service._deliver_alert()` for one alert ID with pre-checks (flag on, expected recipient, expected item, PENDING/FAILED). No new API endpoint.
- Reason: The missing-tests error was caused by `--force-recreate` reusing a stale image, not by the Dockerfile or `.dockerignore` (none exists). Tests are run in-container via `docker exec`, and Jenkins runs pytest on the host, so a separate test stage would change the architecture without fixing anything. A one-off script reuses the production delivery code path while guaranteeing only one alert is sent.
- Alternatives Considered: Multi-stage Dockerfile with a test stage — deferred (optional cleanup). A permanent "dispatch one alert" API endpoint — rejected as unnecessary surface for a one-time test. Calling bulk `dispatch-pending` — rejected, it would also send alerts 5, 6 and 13.
- Status: Active
- Note: DECISION-LOG headings stop at DEC-0010, while code comments cite DEC-0011 to DEC-0033; DEC-0034 was chosen to avoid an ID collision.
