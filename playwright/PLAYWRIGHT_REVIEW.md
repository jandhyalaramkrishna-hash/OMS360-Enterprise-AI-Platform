# Playwright Automation Review — OMS-360

Date: 2026-08-03
Scope: Phase 6 of the QA roadmap ("Playwright Automation") — API + dashboard UI
test automation for the OMS-360 V1 business platform (`app/`), executed
against `http://localhost:8000`.

## 1. Existing Playwright tests (before this pass)

**None.** The repository was searched (recursively, at the root and inside
`tests/`, `verification/`, `Student_Practice_Kit/`, `student-practice-kit-src/`)
for any `playwright.config.*`, `*.spec.ts`, `*.spec.js`, or `package.json`
referencing `@playwright/test`. No matches were found anywhere in the repo.

The existing `tests/` folder contains **Python `pytest` tests only** — unit
tests (`tests/test_health.py`, `tests/test_inventory.py`, `tests/test_orders.py`,
`tests/test_sql_validation.py`), the full `tests/ai/` unit-test suite, and
`tests/api/ai/` + `tests/integration/` API/integration tests for the AI
Runtime and AI Copilot layers. These are a different, complementary layer
(in-process/unit-level, run via `pytest`) and are untouched by this pass —
per the task instruction, this pass only adds true end-to-end/black-box
Playwright coverage against the running HTTP service, which nothing in the
repository previously provided.

**Conclusion:** there was nothing to review, fix, or de-duplicate in Phase 1/2
of the task — the entire `playwright/` folder delivered alongside this
document is new.

## 2. Missing tests identified (before this pass)

Before this pass, there was **zero black-box automated coverage** of:

- Order Management (`/api/v1/orders*`) — create, list, get, audit trail, idempotency
- Inventory (`/api/v1/inventory*`) — list, low-stock, out-of-stock, alerts, history, get, restock, update, create
- Health (`/`, `/version`, `/health`) and Metrics (`/metrics`)
- AI Runtime (`/api/v1/ai/*`) — health, config, providers, features, metrics, status, platform/health
- AI Copilot (`/api/v1/ai/copilot/*`) — all 18 endpoints (ask, questions, catalog, 4 intent-detail endpoints, executive-summary, business-insights, provider-status, 2 root-cause endpoints, qa-assistant, docs-assistant, learning topics/ask)
- All four operational dashboards as rendered UI (Operations, Inventory, Monitoring, AI Copilot) — element rendering, the Inventory dashboard's Add/Update modals, the Monitoring dashboard's alert/health panels, the AI Copilot dashboard's Business Question / SQL Explorer / Executive Summary / Business Insights panels
- Any end-to-end flow tying an API action (placing an order) to its visible effect elsewhere (inventory decrement, audit trail, dashboard KPIs)

All of the above are now covered — see §4.

## 3. Improvements made to existing automation

Not applicable — there was no existing Playwright automation to fix,
de-duplicate, or improve (see §1). No locators were broken, no duplicate
specs existed, and no assertions needed strengthening, because nothing
existed yet.

## 4. What was built in this pass

A new, self-contained Playwright project under `playwright/`:

```
playwright/
  package.json              @playwright/test ^1.48.0, TypeScript ^5.5.4
  playwright.config.ts       baseURL http://localhost:8000, HTML+list+json
                              reporters, screenshot on failure, trace on
                              first retry (retries: 1), video on failure
  tsconfig.json
  utils/apiHelpers.ts         shared helpers: valid order payload builder
                              (matches app/schemas.py exactly), unique
                              mobile/Idempotency-Key generators, dynamic
                              lookup of a real item_id / intent key / topic
                              key from the live API (no hardcoded IDs that
                              could go stale against a different seed script)
  tests/
    smoke/smoke.spec.ts               11 tests  - fast up/down sanity check
    api/health.spec.ts                 5 tests
    api/metrics.spec.ts                3 tests
    api/orders.spec.ts                21 tests  - positive/negative/boundary
    api/inventory.spec.ts             21 tests  - positive/negative/boundary
    api/ai-runtime.spec.ts            10 tests
    api/ai-copilot.spec.ts            19 tests  - all 18 copilot endpoints
    dashboard/operations-dashboard.spec.ts    7 tests
    dashboard/inventory-dashboard.spec.ts    14 tests
    dashboard/monitoring-dashboard.spec.ts   12 tests
    dashboard/ai-copilot-dashboard.spec.ts    9 tests
    e2e/order-lifecycle.spec.ts        4 tests  - cross-cutting business flows
```

**142 tests total**, confirmed via `npx playwright test --list` (test
discovery only — no execution; see §6). Tagged for selective runs:

| Tag | Count | Meaning |
|---|---|---|
| `@smoke` | 11 | Fast up/down check — API + all 4 dashboard pages load |
| `@regression` | 131 | Every test other than the smoke subset |
| `@positive` | 77 | Valid-input / happy-path behavior |
| `@negative` | 24 | Invalid input, missing fields, unknown IDs |
| `@boundary` | 19 | Exact validation-rule edges (gt=0, ge=0, exact-length regexes) |
| `@e2e` | 4 | Multi-step flows spanning API + dashboard |

Run any subset with `npx playwright test --grep @<tag>` (see
`PLAYWRIGHT_EXECUTION_GUIDE.md`).

### Grounding — nothing here was guessed

Every endpoint path, request field, validation rule, and response field
referenced by these tests was taken directly from the application source
read this session, not assumed:

- `app/routes/orders.py`, `app/routes/inventory.py`, `app/routes/health.py`,
  `app/routes/metrics.py`, `app/routes/dashboard.py`
- `app/schemas.py` (validation regexes: mobile `^[6-9]\d{9}$`, pincode `^\d{6}$`;
  `VALID_INVENTORY_STATUSES`; `gt=0`/`ge=0` constraints)
- `app/api/ai/router.py`, `app/api/ai/copilot_router.py`, `app/api/ai/copilot_schemas.py`
- `app/main.py` (route registration, dashboard page routes)
- The four dashboard HTML files under `app/static/` (real element `id`s used
  for every UI locator — no id was invented; where a widget's exact internal
  markup wasn't fully read, e.g. the AI Copilot page's custom combo-box, the
  test says so in a comment and asserts generically instead of guessing a
  class name)

Where the source didn't fully resolve a detail (e.g. whether AI features are
enabled in your `.env`, or the exact intent-key catalog), tests either query
the live API first to discover the real value (`getFirstIntentKey`,
`getFirstLearningTopic`, `getOrderableItemId` in `utils/apiHelpers.ts`) or
accept a range of non-5xx outcomes and explain why in a comment, rather than
asserting a specific value that would be a guess.

## 5. Coverage summary vs. the requested categories

| Requested category | Covered by |
|---|---|
| Order Management | `tests/api/orders.spec.ts`, `tests/e2e/order-lifecycle.spec.ts` |
| Inventory | `tests/api/inventory.spec.ts`, `tests/dashboard/inventory-dashboard.spec.ts` |
| Dashboard | `tests/dashboard/*.spec.ts` (all 4 dashboards) |
| Monitoring | `tests/dashboard/monitoring-dashboard.spec.ts` |
| AI Runtime | `tests/api/ai-runtime.spec.ts` |
| AI Copilot | `tests/api/ai-copilot.spec.ts`, `tests/dashboard/ai-copilot-dashboard.spec.ts` |
| Smoke | `tests/smoke/smoke.spec.ts` (+ `@smoke` tag) |
| Regression | `@regression` tag (131 of 142 tests) |
| End-to-End workflow | `tests/e2e/order-lifecycle.spec.ts` |
| Positive | `@positive` tag (77 tests) |
| Negative | `@negative` tag (24 tests) |
| Boundary | `@boundary` tag (19 tests) |

Not covered, and out of scope for this pass because no source exists for
them in `app/` (confirmed absent, not assumed — see `docs/governance/MODULE-STATUS.md`):
Restaurant Management and Menu Management have no dedicated routes in this
codebase (folded into inventory, per governance notes), so there is nothing
distinct to automate for them yet.

## 6. Execution status — read this before trusting any pass/fail claim

**No test in this suite has been run.** This cloud environment has no
network path to your `localhost:8000`, and no shell-execution bridge to your
machine was available this session. What *was* verified here:

- `npx tsc --noEmit` — the whole suite type-checks cleanly.
- `npx playwright test --list` — Playwright discovers all 142 tests with no
  config or syntax errors, confirming `playwright.config.ts`, `package.json`,
  and every spec file are structurally valid.

Neither of those executes a single HTTP request or opens a browser page — they
prove the suite is ready to run, not that it passes. `docs/QA_Documents/PLAYWRIGHT_EXECUTION_REPORT.md`
and Phase 6's manual-test cross-check are placeholders pending your local run;
see `PLAYWRIGHT_EXECUTION_GUIDE.md` for the exact command
(`RUN_PLAYWRIGHT.bat`) and what to send back.
