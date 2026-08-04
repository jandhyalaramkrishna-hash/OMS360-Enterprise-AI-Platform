# TC-GAP-01 — Missing Test Case Coverage (newly written, 2026-08-03)

**Purpose:** Task 4 required reviewing every existing test case before writing anything new, and creating only what's genuinely missing — not duplicating `docs/TEST_PLAN.md`, `docs/qa/TC-01-...`, or `Student_Practice_Kit/docs/TEST_CASES.md`. This document contains **only** cases that were not already covered anywhere in the repository. It does not restate FUNC/API/NEG/ORD/LIC/SYS/TC cases that already exist — see `TEST_CASE_COVERAGE.md` for where those live.

Three categories were requested by name in the consolidation task and had no dedicated home anywhere in the repo: **Boundary Value**, **Smoke**, and **Dashboard** test cases. They're written below, grounded strictly in behavior already documented elsewhere in this repo (`docs/TEST_PLAN.md`, `docs/RUN_GUIDE.md`, `docs/release/SPRINT-LOG.md`, `Student_Practice_Kit/docs/API_GUIDE.md`) — nothing here asserts a business rule that isn't already written down somewhere else in the project.

---

## 1. Boundary Value Test Cases (V1 platform)

Existing test cases assert *that* validation happens (`docs/TEST_PLAN.md` NEG-01/02, `ORD-NEG-01/02` in the Student kit); none of them assert the exact **boundary**. These do.

| ID | Field / Rule | Boundary Under Test | Steps | Expected |
|---|---|---|---|---|
| BND-01 | Order quantity lower bound | `quantity = 0` vs `quantity = 1` | POST an order with `quantity: 0`, then repeat with `quantity: 1` | `0` → 422 (Pydantic `gt=0`, per `docs/TEST_PLAN.md` NEG-01); `1` → 201, accepted as the minimum valid value |
| BND-02 | Mobile number length | 9, 10, and 11 digits, all starting with a valid 6–9 prefix | POST orders with `mobile` of each length | 9 and 11 digits → 422; exactly 10 digits → passes format validation (per `API_GUIDE.md`'s documented rule: "exactly 10 digits starting with 6–9") |
| BND-03 | Mobile number leading-digit boundary | Prefix digits 5, 6, and 9 | POST orders with otherwise-valid 10-digit mobiles starting `5xxxxxxxxx`, `6xxxxxxxxx`, `9xxxxxxxxx` | `5...` → 422 (below the documented 6–9 range); `6...` and `9...` → pass format validation (both ends of the valid range) |
| BND-04 | Pincode length | 5, 6, and 7 digits | POST orders with each pincode length | 5 and 7 digits → 422; exactly 6 digits → passes format validation (per `docs/TEST_PLAN.md` API-05 and `API_GUIDE.md`) |
| BND-05 | Stock exactly at the requested quantity | `quantity == remaining_stock` vs `quantity == remaining_stock + 1` | Order exactly the remaining stock, then attempt to order one more than what's left | Exact match → 201, stock goes to 0, item should then appear in `GET /api/v1/inventory/out-of-stock`; one over → 409 `insufficient_stock` (per `docs/TEST_PLAN.md` API-02) |
| BND-06 | Idempotency-Key TTL edge | A repeat request sent just inside vs. just outside the documented TTL window | Resend the same `Idempotency-Key` request just before and just after the TTL expires | Inside TTL → 409 `duplicate_order` (per API-03); outside TTL → 201, a genuinely new order is created (this specific "just after expiry" case is not exercised by any existing test — `docs/TEST_PLAN.md` only proves the "within TTL" half) |
| BND-07 | Rate limit boundary (Student kit's own AI platform, and any future V1 rate limiting) | 20th vs. 21st request in the 60s window | N/A on V1 today — no rate limiting exists yet on `/api/v1/orders` per current `docs/TEST_PLAN.md`/`API_GUIDE.md`. Documented here as a **placeholder boundary case to activate if/when rate limiting is added to the order API**, mirroring the already-specified chatbot pattern (`APITEST-01` API-07) | N/A — flagged, not executable against current code |

## 2. Smoke Test Suite (V1 platform + AI platform)

No document anywhere names a specific "smoke suite." Per Task 4's "if something is already available, reuse it," this is a **curated subset of existing cases** — not new content — selected as the minimum set that proves the whole stack is alive after any deploy, in priority order and expected total run time under 2 minutes.

| Order | Reused From | Case | Why it's in the smoke suite |
|---|---|---|---|
| 1 | `docs/TEST_PLAN.md` API-08 | `GET /health` returns 200 | Proves the process is up and can reach its dependencies at all |
| 2 | `docs/TEST_PLAN.md` API-09 | `GET /metrics` returns 200 | Proves the metrics subsystem didn't crash on boot |
| 3 | `docs/TEST_PLAN.md` FUNC-01 | Place one valid order | Proves the full write path (validation → DB → inventory decrement) works end to end |
| 4 | `docs/TEST_PLAN.md` FUNC-05 | Retrieve that order by ID | Proves the read path works |
| 5 | `Student_Practice_Kit/docs/TEST_CASES.md` SYS-04 | `GET /api/v1/ai/platform/health` returns 200 | Proves the AI platform's 393-test-covered code didn't regress at the integration boundary |
| 6 | `docs/RUN_GUIDE.md` §7 | Open `/dashboard/operations` and confirm it loads without a JS console error | Proves the dashboard layer is serving, not just the API |

**Recommendation:** wire these six as an explicit `tests/smoke/test_smoke.py` (or a pytest marker, `@pytest.mark.smoke`, applied to the existing five underlying tests plus one new dashboard-load check) rather than leaving "smoke" as an implicit reading of the full suite — this is a process/tooling recommendation, not a new test case, so it's called out here rather than acted on without your say-so.

## 3. Dashboard Test Cases (all four dashboards — genuinely missing)

`verification/screenshots/` only covers Operations and Monitoring, captured before the Inventory Dashboard (DEC-0031) and AI Copilot Dashboard (DEC-0033) existed, and it's evidence from a manual pass, not a repeatable test-case document. No dashboard has a written test case anywhere. These are new, scoped to what's independently documented in `docs/release/SPRINT-LOG.md` and `docs/RUN_GUIDE.md` about what each dashboard is supposed to show.

| ID | Dashboard | Steps | Expected |
|---|---|---|---|
| DASH-01 | Operations (`/dashboard/operations`) | Load the page after placing at least one order | Order appears in the live feed within one 6-second poll cycle (per `docs/RUN_GUIDE.md` §7/§9); KPI bar renders with no console errors |
| DASH-02 | Monitoring (`/dashboard/monitoring`) | Stop the Kafka container, reload the page | Kafka tile shows `DOWN`/`DEGRADED` within one refresh cycle (per `docs/RUN_GUIDE.md` §10); restart Kafka, confirm the tile recovers on the next poll |
| DASH-03 | Inventory (`/dashboard/inventory`) | Open the dashboard, click "Update Inventory," change Stock and click Save | Change is reflected in the table without a manual page refresh; a corresponding row appears in `inventory_ledger` (per `docs/release/SPRINT-LOG.md` 2026-07-26 entry — this is the exact feature that entry documents but never got a dedicated test-case document, only the ad hoc `tests/test_inventory.py`) |
| DASH-04 | Inventory (`/dashboard/inventory`) | Click "Add New Item," fill the form, save | A new row appears with a server-generated `ITEM-####` ID; item also appears in `GET /api/v1/inventory` |
| DASH-05 | AI Copilot (`/dashboard/ai-copilot`) | Ask a suggested business question (e.g. "how many pending orders") | Answer appears without ever displaying SQL by default; `[View SQL]`/`[Explain SQL]`/`[Related Tables]`/`[Business Flow]` buttons are present and populate on click (per `docs/release/SPRINT-LOG.md` 2026-07-23 AI Copilot Sprint 1 entry's explicit "SQL must never display automatically" requirement) |
| DASH-06 | All four dashboards | Reload each dashboard 3 times in a row | No dashboard throws a browser console error or shows a permanently-empty state when real data exists (basic dashboard smoke check, feeds DASH-01…05 as the fuller version) |

**Note on scope:** these six cases give the four dashboards their first-ever written test coverage, but they are not exhaustive — a full dashboard test pass would also need every card/widget enumerated per dashboard, which requires reading each dashboard's actual HTML/JS (`app/static/*.html`) rather than relying on the sprint narrative alone. That deeper pass is recommended as follow-up work, not done here, to stay within "documentation organization and QA review" scope per your instructions and avoid guessing at UI details not already written down somewhere.

## 4. What was deliberately NOT written here, and why

Per your explicit "only create missing test cases" instruction, this document stops short of inventing test cases for **Restaurant Management, Menu Management, Kitchen Processing (as its own module), Payment Processing, Delivery Management, Notification Service, Audit Trail, or Retry/DLQ handling** as standalone suites. Each of these appears only as an embedded step inside `docs/TEST_PLAN.md`'s order-lifecycle cases (FUNC-03/04, KAFKA-01…05) — real coverage exists for the order-lifecycle *path* through these modules, but not for each module's own edge cases (e.g., what happens if a restaurant has zero active menu items, or a payment gateway callback arrives twice). Writing accurate test cases for those would require reading the actual route/service code under `app/routes/`/`app/services/` for each module first, which goes beyond a documentation-consolidation pass and risks asserting behavior that isn't actually verified against the real code. This gap is recorded explicitly in `TEST_CASE_COVERAGE.md` as a recommendation rather than guessed at here.
