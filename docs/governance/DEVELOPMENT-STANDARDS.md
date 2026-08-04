# DEVELOPMENT-STANDARDS.md — OMS-360

Mandatory for the entire life of the project. Applies to every module, every sprint, no exceptions without a logged decision in `docs/governance/DECISION-LOG.md`.

## 1. Python

- Python 3.11+. PEP8 formatting enforced via `black` + `isort` + `flake8` (or `ruff`).
- Type hints mandatory on all function signatures and Pydantic models; `mypy` clean (or documented suppression with reason).
- No bare `except:` — always catch specific exceptions; use centralized exception handlers for API-facing errors.
- No print statements in application code — use the structured logger only.
- Docstrings (Google or NumPy style) required on all public functions, classes, and modules.
- Dependency injection (FastAPI `Depends`) for DB sessions, config, and shared services — no global mutable state.
- Secrets/config via environment variables (`pydantic-settings` or equivalent) — never hardcoded.

## 2. FastAPI

- One router per module/domain; routers registered explicitly in the app factory — no implicit route discovery.
- Request/response schemas defined with Pydantic models — no raw dicts in/out of endpoints.
- Every endpoint has an explicit `response_model`, status code, and OpenAPI `summary`/`description` (feeds API docs, Rule 7 of the charter).
- Idempotency: all state-mutating endpoints that can be safely retried (e.g., order creation) must accept/honor an idempotency key.
- Centralized exception handlers (`@app.exception_handler`) — consistent error response schema across the API.
- Versioned API prefix (e.g., `/api/v1/...`) from day one.
- `/health` and `/metrics` endpoints mandatory per service before it is deployment-ready.

## 3. React (Operations Dashboard)

- TypeScript, not plain JS.
- Functional components + hooks only; no class components.
- No business logic inside components — data fetching/derivation lives in hooks or a service layer, components render only.
- State management: local state/hooks by default; escalate to a shared store only when genuinely cross-cutting, and document the choice in the Decision Log.
- All API calls go through a single typed API client module — no ad-hoc `fetch`/`axios` calls scattered across components.
- Component and hook names, file names: `PascalCase` for components, `camelCase` for hooks/utilities.
- Accessibility (a11y) baseline: semantic HTML, labeled inputs, keyboard navigable.

## 4. SQL / MySQL

- All schema changes via versioned migrations (e.g., Alembic) — no manual/ad-hoc DDL against any environment.
- Parameterized queries / ORM only — no string-concatenated SQL, ever (SQL injection is a release blocker).
- Every table: explicit primary key, `created_at`/`updated_at` timestamps, and foreign keys enforced (no orphaned references).
- Naming: `snake_case` for tables/columns, singular or plural consistently per the folder standard's decision (to be fixed in Sprint 1 and logged in Decision Log).
- Indexes documented for every query pattern used in hot paths (order lookup, inventory checks, etc.).
- No destructive migration (`DROP`, irreversible `ALTER`) without a reviewed rollback plan.

## 5. Kafka

- Topic naming convention: `oms360.<domain>.<event>.<version>` (e.g., `oms360.order.created.v1`).
- Every consumer is idempotent — safe to reprocess the same message without side-effect duplication.
- Every consumer has a retry policy (bounded retries with backoff) and a Dead Letter Queue topic for exhausted retries.
- Producers must include a message key that guarantees correct partitioning for ordering guarantees where required (e.g., order ID).
- Schemas for event payloads are explicit and versioned (JSON Schema or Avro) — no undocumented ad-hoc payload shapes.
- Consumer group naming: `oms360-<service>-<purpose>`.

## 6. Docker

- Every service ships a `Dockerfile` using multi-stage builds (build stage vs. slim runtime stage).
- No `latest` tags in committed compose files — pin versions.
- No secrets baked into images — runtime environment variables only.
- `docker-compose.yml` at the repo root brings up the full local stack (API, MySQL, Kafka, dashboard) for integration testing.
- Containers run as non-root users.

## 7. PowerShell (dev/ops scripting)

- Scripts use approved verbs (`Get-`, `Start-`, `Stop-`, `New-`, etc.) per PowerShell conventions.
- `Set-StrictMode -Version Latest` and explicit error handling (`try/catch`, `$ErrorActionPreference = 'Stop'`) in all scripts.
- No hardcoded secrets/paths — parameterize scripts and read from environment/config.
- Every script has a comment-based help block (`.SYNOPSIS`, `.DESCRIPTION`, `.EXAMPLE`).

## 8. Documentation

- Every module ships with: README section, API doc entries, DB doc entries (if it owns tables), and test cases — per Rule 7 of the Project Charter.
- All permanent enterprise docs (this file and its siblings listed in `docs/wiki/PROJECT-WIKI.md`) are updated at the end of every sprint, never left stale.
- Comments explain *why*, not *what* — code should be self-explanatory for *what*.
- All decisions that deviate from these standards must be logged in `docs/governance/DECISION-LOG.md` before implementation.

---

*Last updated: 2026-07-19 — Sprint 0.*
