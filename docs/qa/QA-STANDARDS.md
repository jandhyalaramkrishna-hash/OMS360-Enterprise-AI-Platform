# QA-STANDARDS.md — OMS-360

Mandatory QA framework for the entire project life. Product Owner (Ram) is QA Lead and sign-off authority for release checklists.

## 1. Test Strategy

Test-first where practical; every module must have automated test coverage before it is marked Complete in `docs/governance/MODULE-STATUS.md`. Coverage spans unit, integration, contract, and end-to-end (E2E) levels, plus non-functional validation (performance, security, logging).

## 2. Test Levels

| Level | Scope | Tooling (default) |
|---|---|---|
| Unit | Single function/class in isolation, mocked dependencies | `pytest` (+ `pytest-mock`) |
| Integration | Module against real MySQL/Kafka (via Docker Compose test stack) | `pytest` + `testcontainers` or compose-based fixtures |
| Contract | API request/response schema conformance to OpenAPI spec | `schemathesis` or equivalent |
| End-to-End (E2E) | Full order lifecycle across modules via Kafka | `pytest` orchestration scripts / dedicated E2E suite |
| Frontend | React component/behavior tests | `Vitest`/`Jest` + `React Testing Library` |

## 3. Test Naming Convention

- Python: `test_<unit_under_test>_<scenario>_<expected_result>` (e.g., `test_create_order_duplicate_idempotency_key_returns_existing_order`).
- Test files mirror source structure: `tests/unit/...`, `tests/integration/...`, `tests/e2e/...`.
- React: `<ComponentName>.test.tsx`, test names as `it('does X when Y')`.

## 4. API Validation Standards

- Every endpoint tested for: happy path, validation errors (422), auth/authz failures, not-found (404), conflict/idempotency (409/200-replay), and server error handling.
- Response schema validated against the documented `response_model` — no undocumented fields.
- Status codes verified explicitly, not just "2xx".

## 5. SQL Validation Standards

- Every migration tested for apply and rollback.
- Referential integrity tested (foreign key violations rejected as expected).
- No test relies on unindexed full scans for hot-path queries — query plans reviewed for critical paths.
- Parameterization verified — no test constructs raw SQL strings from user input.

## 6. Logging Validation

- Every module's key state transitions (order created, payment processed, delivery assigned, etc.) must emit a structured log entry — verified by test assertions on log output/capture.
- Log entries must include correlation/trace ID (e.g., order ID) to support cross-service tracing.
- No sensitive data (payment details, PII beyond what's necessary) in logs — checked as part of security validation.

## 7. Performance Validation

- Baseline load test per module exposing REST endpoints (e.g., order creation throughput) before it is marked Complete.
- Kafka consumer lag monitored under load; DLQ growth must be bounded/alerted, not silent.
- Performance baselines and thresholds recorded per module as they're established (to be appended here per module once defined).

## 8. Security Validation

- Input validation on all endpoints (Pydantic models enforce types/constraints).
- SQL injection: verified not possible (parameterized queries only, per Development Standards).
- AuthN/AuthZ enforced on all non-public endpoints (mechanism to be defined and logged in Decision Log before Sprint touching auth).
- Secrets scanning in CI before merge (no committed credentials).
- Dependency vulnerability scanning (e.g., `pip-audit`, `npm audit`) as part of the release checklist.

## 9. Regression Checklist

Run before any sprint is marked Complete:

- [ ] All existing unit + integration tests still pass.
- [ ] No previously-fixed defect has reappeared (cross-check against `docs/governance/CHANGE-MANAGEMENT.md` history).
- [ ] API contract tests pass against the current OpenAPI spec.
- [ ] DB migrations apply cleanly on a fresh database and on the previous version's schema.
- [ ] Kafka consumers still process existing event schema versions without error.
- [ ] Dashboard still renders correctly against the current API.

## 10. Release Checklist

- [ ] All Regression Checklist items pass.
- [ ] `/health` and `/metrics` verified on all affected services.
- [ ] README, API docs, DB docs, and test cases updated for every change (Rule 7).
- [ ] `docs/governance/CHANGE-MANAGEMENT.md` updated with this release's changes.
- [ ] `VERSION-HISTORY.md` bumped with the correct semantic version (`vMAJOR.MINOR.PATCH`) and changelog — **mandatory every sprint**, per the permanent versioning policy at the top of that file (DEC-0010).
- [ ] `docs/governance/MASTER-PROJECT-MEMORY.md` updated to reflect current state — **mandatory every sprint** (DEC-0010).
- [ ] `docs/wiki/PROJECT-WIKI.md` updated if the document set changed this sprint (DEC-0010).
- [ ] `docs/governance/MODULE-STATUS.md` updated to reflect new module states.
- [ ] `docs/governance/DECISION-LOG.md` updated if any decisions were made this sprint.
- [ ] `docs/governance/RISK-REGISTER.md` reviewed and updated if new risks were identified or mitigated.
- [ ] Versioned release ZIP produced, named exactly `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform_v<version>.zip` (permanent naming convention, DEC-0010) — **mandatory every sprint**.
- [ ] Product Owner / QA Lead sign-off recorded in `docs/release/SPRINT-LOG.md`.

---

*Last updated: 2026-07-19 — Sprint 0.*
