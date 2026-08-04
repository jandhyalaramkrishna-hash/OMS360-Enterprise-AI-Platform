# VERSION-HISTORY.md — Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

## Versioning Policy (permanent standard, effective 2026-07-19 — DEC-0010)

- **Semantic Versioning (SemVer)** is mandatory for all releases: format `vMAJOR.MINOR.PATCH` (e.g., `v0.1.0`, `v0.2.0`, `v1.0.0`, `v1.1.0`, `v2.0.0`). `0.x.y` = pre-V1-release (active development). `1.0.0` = Version 1 stabilized per `docs/roadmap/PROJECT-ROADMAP.md` Phase 4 completion criteria.
- **Every completed sprint must:** update this file, update `docs/governance/MASTER-PROJECT-MEMORY.md`, update `docs/wiki/PROJECT-WIKI.md` (if the document set changed), and produce a versioned release ZIP.
- **Release ZIP naming convention (permanent):** `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v<version>.zip` — e.g., `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v0.1.0.zip`.
- This policy is binding for all future sprints unless explicitly changed by the Product Owner. See `docs/governance/DECISION-LOG.md` DEC-0010.

Append-only, most recent first.

**Note on version numbering during Sprint 0 (historical, grandfathered):** three entries below are dated 2026-07-19 and two of them carry the tag `v0.1.0`. This predates the versioning policy above and is preserved as an accurate historical record, not corrected retroactively (append-only rule) — see DEC-0007 and DEC-0009 in `docs/governance/DECISION-LOG.md` for why. Every release from this point forward follows the policy above with no ambiguity: exactly one entry per version tag, and the release ZIP filename always matches its version tag exactly.

**Note on the gap between v0.2.0 and v1.0.0 (added 2026-07-20 IST, Sprint 9):** per `docs/governance/DECISION-LOG.md` DEC-0013, the in-repository sprint-code backup ZIPs (`backup/OMS360_v<version>_Sprint<N>.zip`) are a **separate version counter** from this file's documentation-release SemVer tags. Sprints 1–8 each incremented that separate backup counter (`v0.2.0` through `v0.9.0`, one per sprint) without adding a corresponding entry here, since no new *documentation-release* package was produced between Sprint 0's v0.2.0 and this v1.0.0 final release — this was a deliberate, previously-documented consequence of DEC-0013, not an oversight. Full sprint-by-sprint detail for everything built in that gap lives in `docs/release/SPRINT-LOG.md` and `docs/governance/DECISION-LOG.md` (DEC-0012 through DEC-0022).

---

## v1.0.0 — 2026-07-20 (IST) (Sprint 9 — Enterprise Integration; OMS360 ENTERPRISE AI PLATFORM FINAL RELEASE)

**Type:** Application code (AI Enterprise Platform) + documentation. Development on this line is now closed.

**This is the official completion of the OMS360 Enterprise AI Platform**, built incrementally across Sprints 1–9 inside the same repository as the OMS360 v1.2 business platform baseline (DEC-0011), fully isolated from it throughout.

- **Sprint 9 (this release) built `ai/integration/`:** `AIWorkflowService` — a single end-to-end call chain over all five AI modules built in Sprints 1–8 (RAG → MCP → Multi-Agent → Provider Framework → AI Evaluation), reusing every existing collaborator via dependency injection, adding no new retrieval/tool-call/agent-run/evaluation/provider-call logic and no new capability-gating mechanism. `PlatformHealthChecker` — a unified health report aggregating `AIHealthService`, `ProviderHealthChecker`, `MCPHealthChecker`, `AgentHealthChecker`, and an `AIMetrics` snapshot, exposed via the one new route this release adds: `GET /api/v1/ai/platform/health`. See DEC-0022.
- **Cumulative platform, Sprints 1–9:** AI Service Layer scaffolding (Sprint 1) → AI Runtime Infrastructure, feature flags, health, metrics (Sprint 2) → read-only AI API Layer wired into `app/main.py` (Sprint 3) → AI Provider Framework with the first genuinely-callable provider, `MockAIProvider` (Sprint 4) → RAG Foundation with a real (mock) retrieve-then-build-context flow (Sprint 5) → MCP Foundation with a real (mock) tool-call dispatch (Sprint 6) → Multi-Agent Foundation with six mock agents exchanging mock messages (Sprint 7) → AI Evaluation Framework with real accuracy/latency scoring (Sprint 8) → Enterprise Integration chaining all of it together (Sprint 9).
- **393 automated tests pass** (cumulative `pytest` run, up from 351 through Sprint 8), including new true end-to-end integration tests (`tests/integration/`) that assemble the full production-shaped wiring (every real provider, all 4 real MCP tools, all 6 real mock agents, the real built-in RAG documents and eval dataset) and run it to completion.
- **Explicitly still mock-based throughout:** no real vendor LLM (OpenAI/Claude/Gemini/Azure OpenAI) was ever implemented; no real vector database; no real MCP client/transport; no real AI-model-driven agent; no real LLM evaluation service; no Kafka integration was added from `ai/`; no database integration was added from `ai/`; no new external dependency was introduced. This was a constraint honored in every one of the nine sprints, not just this final one.
- **Backward compatibility preserved throughout:** every sprint from 2 onward extended Sprint 1's original scaffolding additively; `tests/ai/test_agents.py` and `tests/ai/test_evals.py` (Sprint 1) still pass completely unmodified after nine sprints of extension.
- **Repository verified clean** before this release: correct folder structure, no duplicate files, `backup/` holding only the latest artifact.
- **Release artifact:** `backup/OMS360_v1.0.0_Final.zip` (repository-internal sprint-code backup, per the DEC-0013 backup counter — see the note above on why this file's own SemVer sequence and that counter are tracked separately, converging here at the same final number).
- **Separately, and NOT resolved by this release:** the underlying OMS360 v1.2 business platform (`app/`) retains only a **spot-verified baseline** (DEC-0011) — the full QA/regression pass against `docs/qa/QA-STANDARDS.md` §9–10 was never in scope for the AI Enterprise Platform sprint sequence and remains open (see `docs/governance/RISK-REGISTER.md` RISK-006, and the open item at the end of `docs/governance/DECISION-LOG.md`).
- Full build-by-build narrative: `docs/release/SPRINT-LOG.md`. Full decision record: `docs/governance/DECISION-LOG.md` (DEC-0012 through DEC-0022). Completion report: `FINAL_RELEASE_REPORT.md` (Sprint 9 / v1.0.0 addendum).
- **Project Status: Completed. Development on the OMS360 Enterprise AI Platform v1.0.0 line is closed.** Any further AI-platform work (real vendor integration, real vector database, real MCP transport, real agent runtime, real LLM evaluation, HTTP-wiring the remaining Sprint 4–9 services) would begin a new, separately-scoped version.

## v0.2.0 — 2026-07-19 (Sprint 0, continued)

**Type:** Documentation module import (no application code)

- Imported and froze the AI Customer Support Chatbot documentation module (16 files: BRD, Architecture Understanding, Feature Spec, User Stories, Functional Flow, API Spec, Database Design, Kafka Events, and a full QA suite) under `ai-chatbot/` in this Project. Status: "Documentation Complete – Pending Integration with OMS360 Production Baseline."
- Verified all 16 files byte-for-byte against the uploaded archive — no corruption, no truncation.
- Identified and logged: 3 empty placeholder folders in the source archive (Resume Points, Future Enhancements, Diagrams — no files to import) and one pre-existing broken internal cross-reference within the source docs (see `docs/governance/CHANGE-MANAGEMENT.md` CHG-0002).
- Designated `OMS360_v1.2_Production_Release.zip` as the official V1 application baseline (not yet received/verified in this project) — see DEC-0006.
- Updated `docs/governance/MODULE-STATUS.md`, `docs/governance/DECISION-LOG.md`, `docs/governance/RISK-REGISTER.md`, `docs/wiki/PROJECT-WIKI.md`, `docs/governance/MASTER-PROJECT-MEMORY.md` accordingly. All 15 Version 1 modules remain **Not Started** in this project's memory — not marked complete on the basis of external documentation alone.
- **Release artifact note:** Product Owner requested the release package be named `OMS360_AI_Enterprise_v0.1.0.zip`. That exact filename is used for the delivered package; this entry's internal semantic version is `v0.2.0` to avoid colliding with the `v0.1.0` entry below, which already covers a different release (the governance-documentation baseline). See DEC-0007.
- No application source code included in this release — none exists in this project yet.

## v0.1.0 — 2026-07-19 (Sprint 0, continued — Official Project Structure Baseline; FROZEN SPRINT 0 RELEASE)

**Type:** Documentation reorganization (no application code)

**Official project name adopted:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

- Reorganized all 29 existing documents (13 governance docs + 16 AI Chatbot documentation-module docs) into the enterprise folder structure: `docs/architecture/`, `docs/business/`, `docs/governance/`, `docs/qa/`, `docs/roadmap/`, `docs/release/`, `docs/wiki/`, plus `VERSION-HISTORY.md` at the project root.
- Updated every internal cross-reference across all 29 documents to the new paths; corrected the one pre-existing broken cross-reference identified in the previous release (`Feature-01-AI-Customer-Support-Chatbot_v1.1.md`).
- Added `README.md` and `PROJECT_CONTEXT.md` at the project root.
- Created structure-only top-level directories for future code (no placeholder files): `backend/`, `frontend/`, `ai/{rag,mcp,agents,evals,prompts}`, `database/`, `kafka/`, `docker/`, `monitoring/`, `tests/`, `scripts/`, `release/`, `backups/`.
- No application source code included — none exists in this project yet. All 15 V1 modules remain **Not Started**.
- Adopted the permanent SemVer + release-naming policy documented above (DEC-0010) — this release is the first to use it.
- **Release artifact:** `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v0.1.0.zip` (supersedes the two earlier ad-hoc-named `OMS360_AI_Enterprise_v0.1.0.zip` / `..._v0.2.0` deliverables from earlier in Sprint 0 — see DEC-0007, DEC-0008, DEC-0009, DEC-0010).
- Sprint 0 is now formally frozen at this version.

## v0.1.0 — 2026-07-19 (Sprint 0)

**Type:** Documentation baseline (no application code)

- Established project charter, roles, and working rules (`docs/governance/PROJECT-CHARTER.md`).
- Established the full enterprise documentation set: MASTER-PROJECT-MEMORY, DECISION-LOG, DEVELOPMENT-STANDARDS, QA-STANDARDS, PROJECT-ROADMAP, PROJECT-FOLDER-STANDARD, RISK-REGISTER, CHANGE-MANAGEMENT, VERSION-HISTORY, PROJECT-WIKI.
- Module status tracker initialized: all 15 Version 1 modules Not Started.
- No code, no schema, no deployable artifact yet.

---

*OMS360 Enterprise AI Platform reached v1.0.0 on 2026-07-20 (IST) and this development line is now closed. The separate, still-open item — a full QA/regression pass on the underlying OMS360 v1.2 business platform baseline — remains tracked in `docs/governance/RISK-REGISTER.md` (RISK-006) for any future, separately-scoped effort.*
