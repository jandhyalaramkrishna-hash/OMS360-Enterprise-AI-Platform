# CHANGE-MANAGEMENT.md — OMS-360

**Every code modification must update this file.** This is the granular change record (distinct from `docs/governance/DECISION-LOG.md`, which records *why* decisions were made, and `VERSION-HISTORY.md`, which records semantic version bumps). Entries are append-only, most recent first.

Format per entry:

```
### CHG-XXXX — <short title>
- Date:
- Sprint:
- Type: Feature | Fix | Refactor | Docs | Config | Infra
- Modules Affected:
- Description:
- Files Changed: (once code exists)
- Docs Updated: README / Architecture / API / DB / Tests / Change Log (list which)
- Linked Decision(s): DEC-XXXX (if applicable)
```

---

### CHG-0004 — Semantic Versioning and release ZIP naming convention established as permanent standard
- Date: 2026-07-19
- Sprint: Sprint 0 (continued — frozen before Sprint 1)
- Type: Docs / Config (process standard)
- Modules Affected: None (project-level process)
- Description: Adopted SemVer (`vMAJOR.MINOR.PATCH`) for all future releases and the permanent release ZIP naming convention `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v<version>.zip`. Documented the mandatory end-of-sprint checklist (update `VERSION-HISTORY.md`, `MASTER-PROJECT-MEMORY.md`, `PROJECT-WIKI.md` if required, produce a versioned release ZIP) in `docs/qa/QA-STANDARDS.md` Release Checklist. This Sprint 0 release itself adopts the new convention: delivered as `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v0.1.0.zip`, replacing the earlier ad-hoc `OMS360_AI_Enterprise_v0.1.0.zip` naming.
- Files Changed: N/A (documentation/process only)
- Docs Updated: `docs/governance/DECISION-LOG.md` (DEC-0010), `VERSION-HISTORY.md` (versioning policy section), `docs/qa/QA-STANDARDS.md` (Release Checklist), `docs/governance/MASTER-PROJECT-MEMORY.md` (Deployment Standards pointer), this file.
- Linked Decision(s): DEC-0010

### CHG-0003 — Official project name adopted; documentation reorganized into enterprise folder structure
- Date: 2026-07-19
- Sprint: Sprint 0 (continued — folder reorg)
- Type: Docs / Config (repository structure)
- Modules Affected: None (project-level structure only; no application modules exist yet)
- Description: Adopted official project name **Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform**. Moved all 29 existing documents into the enterprise folder structure (`docs/architecture/`, `docs/business/`, `docs/governance/`, `docs/qa/`, `docs/roadmap/`, `docs/release/`, `docs/wiki/`, plus root `VERSION-HISTORY.md`). Updated every internal cross-reference across all 29 documents to point at the new paths (verified via automated path-mapping — see verification note in `docs/release/SPRINT-LOG.md`). Corrected the one pre-existing broken cross-reference in `Feature-01-AI-Customer-Support-Chatbot_v1.1.md` (previously pointed at a non-existent filename) to the correct new path. Added two new root files, `README.md` and `PROJECT_CONTEXT.md`. Created structure-only (no placeholder files) top-level directories for future code: `backend/`, `frontend/`, `ai/{rag,mcp,agents,evals,prompts}`, `database/`, `kafka/`, `docker/`, `monitoring/`, `tests/`, `scripts/`, `release/`, `backups/`. No application source code was created.
- Files Changed: N/A (no application repository exists yet — this is a documentation/structure-only reorganization)
- Docs Updated: All 29 pre-existing documents (path references updated in place), plus `docs/governance/MASTER-PROJECT-MEMORY.md` (new Folder Structure section), `docs/wiki/PROJECT-WIKI.md` (full re-index), `VERSION-HISTORY.md` (new entry), `docs/release/SPRINT-LOG.md` (new entry), this file, and two new root files (`README.md`, `PROJECT_CONTEXT.md`).
- Linked Decision(s): DEC-0008, DEC-0009

### CHG-0002 — AI Customer Support Chatbot documentation module imported and frozen
- Date: 2026-07-19
- Sprint: Sprint 0 (continued)
- Type: Docs
- Modules Affected: AI Customer Support Chatbot (V2, documentation-only)
- Description: Verified (byte-for-byte checksum against the uploaded zip) and imported 16 documentation files covering Business Requirements, Architecture Understanding, Feature Spec, User Stories, Functional Flow, API Specification, Database Design, Kafka Events, and a full QA suite (Test Plan, Test Cases, API/SQL/Regression/Performance/AI-specific testing, Interview Questions) for the AI Customer Support Chatbot feature. Stored permanently under `ai-chatbot/` in this Project. No source code was created, inferred, or scaffolded — status recorded as "Documentation Complete – Pending Integration with OMS360 Production Baseline." Identified one pre-existing broken internal cross-reference in the source docs (Feature-01 doc references a filename `API-01-AI-Chatbot_v1.1.md` that does not match the actual delivered filename `API-01-AI-Customer-Support-Chatbot_v1.1.md`) — logged as a known issue, not altered in the original document.
- Files Changed: N/A (no application repository exists yet)
- Docs Updated: `docs/governance/MASTER-PROJECT-MEMORY.md`, `docs/governance/MODULE-STATUS.md`, `docs/governance/DECISION-LOG.md`, `docs/governance/RISK-REGISTER.md`, `VERSION-HISTORY.md`, `docs/wiki/PROJECT-WIKI.md`, `docs/release/SPRINT-LOG.md`, this file.
- Linked Decision(s): DEC-0005, DEC-0006, DEC-0007

### CHG-0001 — Enterprise documentation baseline established
- Date: 2026-07-19
- Sprint: Sprint 0
- Type: Docs
- Modules Affected: None (project-level)
- Description: Created the full permanent enterprise documentation set (MASTER-PROJECT-MEMORY, DECISION-LOG, DEVELOPMENT-STANDARDS, QA-STANDARDS, PROJECT-ROADMAP, PROJECT-FOLDER-STANDARD, RISK-REGISTER, CHANGE-MANAGEMENT, VERSION-HISTORY, PROJECT-WIKI) as mandated by the Product Owner before Sprint 1 can begin. No application code exists yet.
- Files Changed: N/A (documentation-only, no repository yet)
- Docs Updated: All ten enterprise docs created; MASTER-PROJECT-MEMORY, DECISION-LOG cross-referenced.
- Linked Decision(s): DEC-0003, DEC-0004

---

*No application code changes yet. This log activates fully once Sprint 1 implementation begins.*
