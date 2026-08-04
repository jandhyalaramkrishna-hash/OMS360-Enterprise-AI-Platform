# OMS-360 Enterprise Food Delivery Platform — Project Charter

**Status:** ACTIVE — Permanent project memory anchor. Read this doc at the start of every session before doing any work.

**Official Project Name (as of 2026-07-19, DEC-0008):** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform. See root `README.md` and `PROJECT_CONTEXT.md` for the current enterprise folder structure.

## Roles

- **Product Owner / QA Lead:** Ram (jandhyala.ramkrishna@gmail.com)
- **Senior Software Engineer (implementation owner):** Claude, acting in this Project

## Working Rules (binding for all future sprints)

1. Maintain complete project memory within this Project — no relying on chat history alone.
2. Never forget previous sprint work. Always consult `docs/release/SPRINT-LOG.md` and `docs/governance/MODULE-STATUS.md` before starting new work.
3. Never recreate completed modules. Check `docs/governance/MODULE-STATUS.md` first.
4. Before writing code, always review previous project artifacts (docs in this Project, and the codebase's own README/architecture docs).
5. Maintain enterprise coding standards (structured logging, exception handling, idempotency, retry/DLQ patterns, tests) consistent with the project description.
6. Every sprint must update project documentation before being considered done.
7. Every change must include, where applicable:
   - README updates
   - Architecture updates
   - API documentation
   - Database documentation
   - Test cases
   - Change log entry (`docs/release/SPRINT-LOG.md`)
8. Preserve folder structure and coding standards already established by prior sprints — do not restructure without discussing it first.
9. If information needed to proceed is missing or ambiguous, ask the Product Owner instead of assuming.
10. Treat this as a production-grade enterprise system at all times (no throwaway/demo shortcuts unless explicitly agreed).

## Session Start Protocol

At the start of every new chat/session, Claude will:
1. Summarize current project state (from this doc + `docs/governance/MODULE-STATUS.md` + `docs/release/SPRINT-LOG.md` — or start from root `PROJECT_CONTEXT.md`, which points to all of these).
2. List completed modules.
3. List pending work.
4. Continue from the last completed sprint without losing context.

## Tech Stack (as defined by project description)

FastAPI, Apache Kafka, MySQL, Docker, REST APIs. Event-driven architecture with idempotent processing, retry mechanisms, DLQ handling, structured logging, audit trails, health/metrics monitoring, operational dashboards.

## Enterprise Modules (Version 1 scope)

1. Customer Order Management
2. Restaurant Management
3. Menu Management
4. Inventory Management
5. Kitchen Processing
6. Payment Processing
7. Kafka Event Processing
8. Delivery Management
9. Notification Service
10. Health Monitoring
11. Metrics Monitoring
12. Audit Trail
13. Retry & Dead Letter Queue (DLQ)
14. Operations Dashboard
15. API Documentation (Swagger/OpenAPI)

## Future Roadmap (Version 2 — not in scope until V1 is stabilized)

AI-powered Order Validation, AI Fraud Detection, Predictive Inventory Management, AI Delivery ETA Prediction, AI Root Cause Analysis, Live GPS Delivery Tracking, Geofencing, Route Optimization, AI Chat Assistant, Natural Language to SQL, Predictive Business Analytics, Intelligent Dashboard Insights.

## Companion Docs

- `docs/governance/MODULE-STATUS.md` — per-module status tracker (Not Started / In Progress / Complete), updated every sprint.
- `docs/release/SPRINT-LOG.md` — chronological change log, one entry per sprint/change.

## Log

- 2026-07-19 — Charter established. Rules acknowledged. No code or modules exist yet; project is at kickoff. Awaiting first sprint scope from Product Owner.
- 2026-07-19 — Official project name adopted (Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform) and documentation reorganized into the enterprise folder structure. Sprint 0 formally frozen. See DEC-0008, DEC-0009 in `docs/governance/DECISION-LOG.md`.
