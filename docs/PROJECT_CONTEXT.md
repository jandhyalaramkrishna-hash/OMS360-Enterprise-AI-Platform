# PROJECT_CONTEXT.md — Session-Start Primer

**Read this file first, in any new session, before doing any work on this project.** It is a short pointer document — it deliberately does not duplicate content that lives elsewhere. Full detail is always in the linked document, not here.

## Who's Who

- **Product Owner / QA Lead:** Ram (jandhyala.ramkrishna@gmail.com)
- **Senior Software Engineer (implementation owner):** Claude, acting in this Project

Full role definitions and the 10 binding working rules: `docs/governance/PROJECT-CHARTER.md`.

## What This Project Is

**Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform** — an enterprise-grade, event-driven food ordering and delivery management platform (FastAPI, Apache Kafka, MySQL, Docker), with a planned Version 2 of AI-powered enhancements. Full vision, business goals, tech stack, architecture, and module dependency map: `docs/governance/MASTER-PROJECT-MEMORY.md`.

## Current State — Read Before Doing Anything

1. `docs/governance/MASTER-PROJECT-MEMORY.md` — the single source of truth. Start here for "what is the current state of this project."
2. `docs/governance/MODULE-STATUS.md` — per-module status (all 15 V1 modules are currently **Not Started**; the AI Customer Support Chatbot is **Documentation Complete – Pending Integration**).
3. `docs/governance/DECISION-LOG.md` — every decision made, append-only. Check for open items before making a new one.
4. `docs/governance/RISK-REGISTER.md` — active risks, including the current #1 blocker (RISK-005: no application baseline has been provided or verified yet).
5. `docs/release/SPRINT-LOG.md` — narrative history of what happened, sprint by sprint.

## The Current Blocker

Sprint 1 cannot begin until `OMS360_v1.2_Production_Release.zip` — the designated official V1 application baseline (see DEC-0006) — is provided by the Product Owner and verified in this project. Until then: **no application source code is written, scaffolded, or inferred**, per explicit Product Owner instruction. This applies to V1 modules and to the already-fully-designed AI Customer Support Chatbot feature (`docs/business/`, `docs/architecture/`, `docs/qa/`) alike.

## Working Rules (binding — full text in `docs/governance/PROJECT-CHARTER.md`)

Maintain complete project memory in this Project; never forget prior sprint work; never recreate completed modules; review prior artifacts before writing code; maintain enterprise coding standards; update documentation every sprint; every change updates README/architecture/API/DB docs/tests/change log; preserve established folder structure and standards; ask instead of assuming when information is missing; treat this as a production-grade system at all times.

## Folder Structure

See `README.md` at the project root for the full tree, or `docs/governance/MASTER-PROJECT-MEMORY.md` §4 for the authoritative version with rationale for each directory.

## Full Navigation

Every document in this project is indexed in `docs/wiki/PROJECT-WIKI.md`. If you can't find something, look there before assuming it doesn't exist.

---

*This file is a primer, not a substitute for the documents it points to. When in doubt, follow the links.*
