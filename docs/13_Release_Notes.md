# 13 — Release Notes — OMS-360 / Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

**Consolidated:** 2026-08-04 (renumbered from `docs/Release_Notes.md`,
content unchanged). This is the reader-facing summary; the full
append-only, governance-grade version log (with every DEC-#### reference)
remains at `docs/VERSION-HISTORY.md` and is the source of truth if this
document and that one ever appear to disagree — always update
`docs/VERSION-HISTORY.md` first, then reflect the change here.

## v1.0.0 — 2026-07-20 — OMS-360 Enterprise AI Platform (Final Release)

The AI Enterprise Platform (`ai/`) is complete: Provider Framework, RAG,
MCP, Multi-Agent, AI Evaluation, and an Enterprise Integration layer
chaining all five together, exposed via one new endpoint,
`GET /api/v1/ai/platform/health`. **393/393 automated tests pass.**
Explicitly mock-based throughout — no real vendor LLM, vector database,
MCP transport, agent runtime, or evaluation service. Development on this
line is now closed; any future work here (real vendor integration, etc.)
begins a new, separately-scoped version.

Separately, and not resolved by this release: the underlying OMS-360 v1.2
business platform (`app/`) has a spot-verified baseline only — the full
QA/regression pass remains open (tracked as RISK-006 per `docs/VERSION-HISTORY.md`;
see `docs/04_SDLC.md` §10 for a note on this risk not yet being reflected
in `docs/governance/RISK-REGISTER.md`).

## v0.2.0 — 2026-07-19 (Sprint 0, continued)

Imported and froze the AI Customer Support Chatbot documentation module
(16 files — BRD, architecture, feature spec, user stories, API/DB/Kafka
design, and a full QA suite). Status: "Documentation Complete — Pending
Integration." No application code included — this feature has never had
any code written for it.

## v0.1.0 — 2026-07-19 (Sprint 0, continued — Official Project Structure Baseline)

Official project name adopted. Reorganized all 29 existing documents into
the enterprise folder structure (`docs/architecture/`, `docs/business/`,
`docs/governance/`, `docs/qa/`, `docs/roadmap/`, `docs/release/`,
`docs/wiki/`). Added `README.md` and `docs/PROJECT_CONTEXT.md`. Adopted the
permanent SemVer + release-naming policy still in effect today.

## v0.1.0 — 2026-07-19 (Sprint 0)

Project charter, roles, and working rules established. Full governance
documentation set created. All 15 V1 modules marked Not Started. No code
yet.

## Unversioned — V1.2 Production Packaging — 2026-07-18

The OMS-360 v1.2 business platform (`app/`, Docker Compose, MySQL schema)
was packaged for production with launcher scripts
(`START/STOP/RESTART/CHECK_OMS360.bat`), a standalone app-layer compose
file, and structured logging — application source itself was untouched.
13 runtime checks were left explicitly marked "Requires local
verification" rather than assumed passing. Full detail:
`docs/FINAL_RELEASE_REPORT.md`, `docs/12_Test_Summary_Report.md`.

## Unversioned — Backend Stability Audit — 2026-07-22

Found and fixed 4 defects preventing the app from starting or serving
correct data: an undefined-name import crash, 3 mismatched ORM column
mappings, and a broken MySQL init-script mount path. All fixed in
code/config only — the schema itself was not modified. Full detail:
`docs/11_Defect_Report.md` DEF-001 through DEF-003.

## Unversioned — QA Automation Pipeline Built — 2026-08-03/04

Enterprise Newman (Postman) + pytest/Allure + Jenkins QA infrastructure
built from scratch: a real 56-request/168-assertion Postman collection
generated from live route source, unified Allure reporting with trend
history (dark-theme-by-default), a Jenkins pipeline that never
auto-starts the application, and a fully reorganized, numbered
documentation set (`docs/01`–`19` + `docs/README.md`). Two real defects
found and fixed same-day (PowerShell reporter-list corruption, Allure
`file://` viewing issue) — see `docs/11_Defect_Report.md` DEF-005.

---

*Versioning policy: Semantic Versioning (`vMAJOR.MINOR.PATCH`) is
mandatory for all releases — see `docs/VERSION-HISTORY.md` for the full
policy and every historical entry, including the Sprint 0 grandfathered
entries this summary condenses.*
