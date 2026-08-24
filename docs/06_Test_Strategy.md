# 06 — Test Strategy — OMS-360 Enterprise QA

**Consolidated:** 2026-08-04 (renumbered from `docs/Test_Strategy.md`;
`Regression_Test_Checklist.md` folded into §11 below rather than kept as a
separate file, per the 2026-08-04 reorganization). Originally distilled
from `docs/qa/QA-STANDARDS.md` plus the real Newman/pytest/Allure/Jenkins/
Playwright tooling built into this repo. **Update, final documentation
cleanup pass (2026-08-04):** `docs/qa/` (including `QA-STANDARDS.md`) is
now retired — this document is its sole replacement. Nothing was lost:
`QA-STANDARDS.md`'s only content not already reflected below was generic
React/frontend test-naming boilerplate (`frontend/` is an empty, unused
directory in this repo — see `README.md`), which does not apply here. This
is the "how we test, and with what" document; `docs/07_Test_Plan.md` is
the "what we test" document (including the V2 chatbot spec, §8).

## 1. Strategy Statement

Test-first where practical. Every module must have automated test
coverage before it is marked Complete in `docs/governance/MODULE-STATUS.md`.
Coverage spans unit, integration, API/contract, and end-to-end (E2E)
levels, plus non-functional validation (performance, security, logging) —
see `docs/03_SRS.md` §3 for the non-functional requirement list this
strategy exists to verify.

## 2. Test Levels and Tooling (as actually implemented in this repo)

| Level | Scope | Tooling | Where it lives |
|---|---|---|---|
| Unit | Single function/class in isolation, mocked dependencies | `pytest` | `tests/` |
| Integration | Module against real MySQL/Kafka | `pytest` against the Docker Compose stack | `tests/integration/`, `tests/ai/` |
| API / Contract | Request/response conformance to the real FastAPI routes | Postman collection (56 requests, 168 assertions) run via **Newman** | `postman/collection/OMS360.postman_collection.json` |
| End-to-End (browser) | Full dashboard/page behavior in a real browser | **Playwright** | `playwright/` |
| End-to-End (order lifecycle) | Full order → kitchen → delivery → payment flow via Kafka | Manual + `docs/07_Test_Plan.md` §4 (Kafka steps are currently manual — see Gap below) | `docs/07_Test_Plan.md` |
| Reporting | Unify Newman + pytest results into one report with trend history | **Allure** (`allure-pytest`, `newman-reporter-allure`) | `allure-results/`, `allure-report/` |
| CI Orchestration | Run the above on every build, fail fast if the stack isn't up, archive everything even on failure | **Jenkins** declarative pipeline | `jenkins/Jenkinsfile` |

## 3. Test Naming Convention

- Python: `test_<unit_under_test>_<scenario>_<expected_result>` (e.g.,
  `test_create_order_duplicate_idempotency_key_returns_existing_order`).
- Test files mirror source structure: `tests/unit/...`, `tests/integration/...`,
  `tests/e2e/...`.
- Postman: numbered folders by module (`01 - Health & Metrics` … `07 -
  Dashboard Pages`), each request carrying its own `pm.test()` assertions.

## 4. API Validation Standards

Every endpoint tested for: happy path, validation errors (422),
not-found (404), conflict/idempotency (409), and server error handling
(500, no stack trace). Response schema validated against the documented
`response_model` — no undocumented fields. Status codes verified
explicitly, not just "2xx". See `docs/09_API_Test_Cases.md`.

## 5. SQL Validation Standards

Every migration tested for apply and rollback. Referential integrity
tested. No test relies on unindexed full scans for hot-path queries.
Parameterization verified — no test constructs raw SQL strings from user
input. See `docs/07_Test_Plan.md` §3, `tests/test_sql_validation.py`.

## 6. Logging Validation

Every module's key state transitions must emit a structured log entry.
Log entries must include a correlation/trace ID (order ID) for
cross-service tracing. No sensitive data in logs.

## 7. Performance Validation

Baseline load test per module exposing REST endpoints before it's marked
Complete. Kafka consumer lag monitored under load; DLQ growth must be
bounded/alerted, not silent. **Gap, disclosed:** no automated performance
test currently exists for V1 — this is a recommendation, not yet executed
(see `docs/12_Test_Summary_Report.md`).

### 7.1 V2 — AI Customer Support Chatbot Performance Plan (documented, not built)

Migrated in from the former `docs/qa/PERF-01-AI-Customer-Support-Chatbot_v1.1.md`
(folder retired 2026-08-04).

**Latency Budgets (p95)**

| Component | Target | Notes |
|---|---|---|
| Identity check + history load (DB only) | < 100 ms | Simple indexed queries |
| LLM call (no tool) | < 1.5 s | FAQ-only answer |
| LLM call (1 tool round-trip) | < 3 s | Most common case (order status/ETA) |
| Total API response time | < 3.5 s | End-to-end, matches existing `HTTP_CLIENT_TIMEOUT_SECONDS`-style timeout philosophy |
| Fallback on provider timeout | ≤ configured timeout + 200ms | Must never hang the customer |

**Load Test Scenarios**

| Scenario | Setup | Pass Criteria |
|---|---|---|
| Concurrent conversations | 100 simultaneous distinct conversation_ids, 1 msg/sec each | p95 latency within budget, 0 cross-conversation data mixing |
| Sustained order-status queries | 500 requests/min for 10 min, mock provider | No memory leak, no connection pool exhaustion on the DB side |
| Rate-limit correctness under load | 1 mobile number sending 100 req/min | 429 returned consistently after threshold, no false positives for other mobiles |
| Mixed flag states | 50% of instances flag ON, 50% OFF (rolling deploy simulation) | No crash, no shared-state corruption |
| DB growth | Simulate 10,000 conversations / 60,000 messages | Query plans for history/identity-check remain index-backed (EXPLAIN shows index usage, not full table scan) |

**Cost Control Validation** (LLM-specific "performance" concern): verify
conversation-summary compression actually triggers at the documented
6-turn threshold (`docs/07_Test_Plan.md` §8.3 Context Window Test) —
without it, token cost grows unbounded per long conversation. Verify
system prompt + tool schema token count stays within the documented
~700 token estimate, regression-tested if the prompt is ever edited.
Verify the 1000-character input cap is enforced server-side, not just
documented.

**Degradation Behavior Under Provider Slowness**

| Provider latency | Expected system behavior |
|---|---|
| Normal (<3s) | Normal reply |
| Slow (3–8s) | Reply still returned, flagged in logs for SRE visibility |
| Timeout (>configured limit) | Graceful fallback reply, logged as a failure, does not retry indefinitely |
| Provider fully down | Circuit breaker (recommended pattern) trips after N consecutive failures, short-circuits to fallback for a cooldown window |

**Non-Functional Pass Criteria for Sign-off:** p95 total response time
within budget under the 100-concurrent-conversation load test; rate
limiting has 0 false positives/negatives; no degradation to
`POST /api/v1/orders` latency when the chatbot is under load (proves
resource isolation).

## 8. Security Validation

Input validation on all endpoints (Pydantic). SQL injection: verified not
possible (parameterized queries only). AuthN/AuthZ: **not yet
implemented anywhere in V1** — a known, documented gap, not silently
assumed away (see `docs/02_BRS.md` §1.6). Secrets scanning and dependency
vulnerability scanning: recommended, not yet wired into `jenkins/Jenkinsfile`.

## 9. Execution Flow (identical locally and in Jenkins)

1. `START_OMS360.bat` starts the application. QA tooling **never** starts
   Docker or the app itself — verification only.
2. `Setup_QA_Environment.bat` — one-time per machine (Node/npm/Java/Python
   verified, Newman + reporters + Allure CLI auto-installed).
3. `Run_QA_Pipeline.bat` — daily. Verifies the stack
   (`postman/verify_stack_health.py`), fails immediately with an explicit
   message if it isn't up, then runs Newman, then `pytest`, then generates
   and verifies (`postman/verify_allure_report.py`) one unified Allure
   report with preserved trend history.
4. `jenkins/Jenkinsfile` mirrors this exact flow in CI — see
   `docs/19_Jenkins_Pipeline.md`.

## 10. Known Gaps in This Strategy (disclosed, not hidden)

- Kafka validation (`docs/07_Test_Plan.md` §4) is entirely manual — no
  automated Kafka integration test exists yet, the single largest gap
  relative to how central Kafka is to this project's architecture.
- No dedicated QA document suite exists yet for the `ai/` AI Copilot layer
  despite it having 393+ passing automated tests — see
  `docs/12_Test_Summary_Report.md` for the coverage asymmetry this leaves.
- No performance/load testing tooling is wired in yet (§7).
- No security/dependency scanning is wired into the Jenkins pipeline yet (§8).

## 11. Regression Checklist

Run before any sprint is marked Complete. Folded in below from the former
standalone `Regression_Test_Checklist.md` (consolidated originally from
`docs/qa/QA-STANDARDS.md` §9 and `docs/qa/REG-01-AI-Customer-Support-Chatbot_v1.1.md`
— both now retired, 2026-08-04 final documentation cleanup; this section is
their sole replacement).

### 11.1 V1 — OMS-360 Business Platform Regression Checklist

- [ ] All existing unit + integration tests still pass.
- [ ] No previously-fixed defect has reappeared — cross-check
      `docs/11_Defect_Report.md` against current behavior.
- [ ] API contract tests pass against the current OpenAPI spec — run the
      full Newman collection (`docs/09_API_Test_Cases.md` §1).
- [ ] DB migrations apply cleanly on a fresh database and on the previous
      version's schema.
- [ ] Kafka consumers still process existing event schema versions
      without error.
- [ ] Dashboard still renders correctly against the current API.

**This checklist is what `Run_QA_Pipeline.bat` and `jenkins/Jenkinsfile`
actually execute on every run** — Newman (168 assertions across the API
surface) plus the full `pytest` suite, both feeding one Allure report so a
regression is visible immediately, not just assumed passed. See §9 above
for the exact execution flow.

### 11.2 V2 — AI Customer Support Chatbot Regression Checklist (documented, not built)

**Why regression risk is low here (and how to prove it):** this feature
adds new files/tables/endpoints/one Kafka topic. It does not modify
`order_service.py`, `consumer.py`, `producer.py`, `inventory_service.py`,
`payment_service.py`, `kitchen_service.py`, `delivery_service.py`, or any
existing route file's existing handlers. The checklist below exists to
*prove* that claim, not assume it.

Included for completeness — this proves the chatbot feature, when built,
adds new files/tables/endpoints/one Kafka topic **without modifying**
`order_service.py`, `consumer.py`, `producer.py`, `inventory_service.py`,
`payment_service.py`, `kitchen_service.py`, `delivery_service.py`, or any
existing route handler.

| # | Check | Method | Expected |
|---|---|---|---|
| 1 | Full existing automated suite passes unchanged | `pytest tests/` with feature flag OFF | Same as pre-feature baseline |
| 2 | Full existing automated suite passes with flag ON | `pytest tests/` with `ai_chatbot_enabled=true` | Identical to #1 — proves no side-effect leakage even when active |
| 3 | Order creation → fulfillment lifecycle unaffected | Create a real order, let it flow to DELIVERED | Same state transitions, audit entries, timing as before this feature existed |
| 4 | Existing dashboard endpoints unchanged in shape | Diff JSON response shape before/after | No new required fields, no removed fields, no type changes |
| 5 | Existing Kafka topics unaffected | Monitor topics during a chatbot load test | No unexpected messages, no consumer lag increase attributable to chatbot |
| 6 | Inventory module unaffected | Run existing inventory scenarios | Behavior identical |
| 7 | Health/metrics still report correctly | `GET /health`, `GET /metrics` | Optional additive AI-health field only, all existing fields unchanged |
| 8 | DB migration is idempotent | Run `migrations/004_add_ai_chatbot_tables.sql` twice | Second run is a no-op, no error |
| 9 | Flag OFF leaves zero footprint on request latency | Load test `POST /api/v1/orders` with chatbot deployed but flag off | Latency within normal baseline |
| 10 | No new required env var breaks existing deployments | Boot with pre-feature `.env` | App boots; `ai_chatbot_enabled` defaults false; no crash on missing `AI_API_KEY` |

**Sign-off criteria:** all 10 checks green, on both flag states (ON/OFF),
before this feature can move from "Design Complete" to "Approved for Build."

## 12. Release Checklist

- [ ] All Regression Checklist items pass (§11 above).
- [ ] `/health` and `/metrics` verified on all affected services.
- [ ] README, API docs, DB docs, and test cases updated for every change.
- [ ] `docs/governance/CHANGE-MANAGEMENT.md` updated with this release's changes.
- [ ] `docs/13_Release_Notes.md` (and `docs/VERSION-HISTORY.md`) bumped with the correct semantic version.
- [ ] `docs/governance/MASTER-PROJECT-MEMORY.md` updated to reflect current state.
- [ ] `docs/governance/MODULE-STATUS.md` updated to reflect new module states.
- [ ] `docs/governance/DECISION-LOG.md` updated if any decisions were made this sprint.
- [ ] `docs/governance/RISK-REGISTER.md` reviewed and updated.
- [ ] Versioned release ZIP produced per the naming convention in `docs/VERSION-HISTORY.md`.
- [ ] Product Owner / QA Lead sign-off recorded in `docs/release/SPRINT-LOG.md`.

---

*Product Owner (Ram) is QA Lead and sign-off authority for all release checklists.*
