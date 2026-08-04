# TEST_CASE_COVERAGE.md — OMS-360 / Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

**Generated:** 2026-08-03
**Basis:** Every document in `docs/QA_DOCUMENT_INVENTORY.md`, cross-checked against the actual automated suite under `tests/` (read via directory listing: `test_health.py`, `test_orders.py`, `test_inventory.py`, `test_sql_validation.py`, plus 50+ files under `tests/ai/`, `tests/api/ai/`, `tests/integration/`).

**A note on how to read the percentages below**, in keeping with this project's own stated ethos (`docs/governance/FINAL_RELEASE_REPORT.md`: "nothing claims a runtime test passed unless it was actually executed"): these are **documentation-coverage estimates** — how much of each category has a written test case or a real automated test *somewhere* in the repo — not a live pass/fail rate. This session did not execute `pytest`. Where the repo's own records (`docs/release/SPRINT-LOG.md`) already report a real, executed pass/fail count, that's cited directly instead of estimated.

---

## Available Test Cases (by document)

| Source | Count | Product Line |
|---|---|---|
| `docs/TEST_PLAN.md` | 7 Functional + 11 API + 9 SQL queries + 5 Kafka steps + 7 Negative = **39 cases** | V1 business platform |
| `Student_Practice_Kit/docs/TEST_CASES.md` | 5 Licensing + 5 Order + 6 Order-Negative + 5 Inventory + 4 System + 2 Expiry = **27 cases** (≈16 overlap with `TEST_PLAN.md`'s scope) | V1 platform, packaged distribution |
| `docs/qa/TC-01-...` | **24 cases** | V2 chatbot (not built) |
| `docs/qa/APITEST-01-...` | **19 cases** | V2 chatbot (not built) |
| `docs/qa/SQL-01-...` | **9 queries** | V2 chatbot (not built) |
| `docs/qa/REG-01-...` | **10-point checklist** | V2 chatbot (not built) |
| `docs/qa/PERF-01-...` | 5 latency budgets + 5 load scenarios | V2 chatbot (not built) |
| `docs/qa/AITEST-01-...` | 7 groundedness + 5 adversarial + 5 tool-matrix + 5 escalation = **22 cases** | V2 chatbot (not built) |
| `TC-GAP-01-Missing-Coverage.md` (new, this session) | 7 Boundary + 6 Smoke (curated, reused) + 6 Dashboard = **19 cases**, 13 genuinely new | V1 platform |
| **Total distinct, documented test cases** | **≈170** | Mixed |

## Missing Test Cases

- Dedicated suites for Restaurant Management, Menu Management, Kitchen Processing, Payment Processing, Delivery Management, Notification Service, Audit Trail, Retry/DLQ — see `TC-GAP-01-Missing-Coverage.md` §4 for why these weren't fabricated in this pass.
- A Requirements Traceability Matrix (RTM) linking any test case above back to a specific requirement/user story — none exists.
- A Kafka-specific test document for the V2 chatbot's own `ai.chatbot.escalated` topic (it has every other category but this one).
- Deeper per-widget dashboard test cases (see `TC-GAP-01` §3's scope note).
- Formal SDLC/STLC/Test Closure Report documents — process is well-governed via `docs/governance/*` but not in these specifically-named formats.

## Coverage by Category

| Category | Estimate | Basis |
|---|---|---|
| **Positive Coverage** | ~85% | Strong: FUNC-01/02/05/07, ORD-01…05, TC-01/04/05/07/08/10/18/19/20, DASH-01/03/04/05 (new). Gap: no positive-path cases for restaurant/menu/notification modules specifically. |
| **Negative Coverage** | ~80% | Strong: NEG-01…07, ORD-NEG-01…06, API-01…07, TC-02/03/06/09/13/14/15/16/17/21/22, BND-01…07 (new). Gap: no negative cases for payment-gateway failure modes or notification-delivery failure. |
| **Business Flow Coverage** | ~55% | The single most important flow — order → kitchen → delivery → payment (FUNC-03/04, KAFKA-01/02) — is well covered narratively, but each module's *own* internal flow (e.g., a restaurant closing mid-order, a menu item being deactivated mid-order) has no documented case. |
| **API Coverage** | ~65% | Orders, Inventory, Health, Metrics, and (for the unbuilt V2 feature) Chatbot are all well covered on paper. Dashboard APIs and AI Copilot APIs have real automated tests (`tests/api/ai/test_copilot_routes.py`) but no human-readable QA test-case document. |
| **Database / SQL Coverage** | ~65% | `docs/TEST_PLAN.md` §3 + `SQL-01` + the real, executing `tests/test_sql_validation.py` cover orders/inventory well. No SQL validation doc exists for `kitchen_status`, `delivery_status`, or `order_audit_trail` in isolation — only as part of the order-lifecycle query set. |
| **Kafka Coverage** | ~50% | `docs/TEST_PLAN.md` §4 (KAFKA-01…05) is thorough but entirely **manual** — there is no automated Kafka integration test anywhere in `tests/`. This is the single largest gap relative to how central Kafka is to the project's own stated architecture. |
| **Dashboard Coverage** | ~35% (up from ~15% before this session's `TC-GAP-01`) | Before this session: only 2 of 4 dashboards had any evidence at all (dated screenshots, no repeatable test cases). After: all 4 dashboards have at least one written test case each (`DASH-01…06`), but none have been executed, and per-widget depth is still shallow. |
| **AI Runtime / AI Copilot Coverage** | ~90% automated, ~10% as human-readable QA documents | This is the project's biggest coverage *asymmetry*, worth flagging on its own: the `ai/` platform has a genuinely excellent, executed automated suite (393/393 passing per `docs/release/SPRINT-LOG.md`'s Sprint 9 entry, growing further through the AI Copilot sprints), but essentially none of that is captured as a QA test-case *document* the way the (unbuilt) V2 chatbot is — the chatbot has 5 full QA documents and zero lines of code; the AI Copilot has thousands of lines of tested code and effectively zero QA documents. If audit/portfolio presentation matters here, that asymmetry is worth correcting by writing a QA doc suite for the AI Copilot mirroring the chatbot's own `TP/TC/APITEST/SQL/REG` pattern — a natural next task, not attempted in this session to stay within "reuse and consolidate, don't build new suites wholesale" scope. |

## Recommendations

1. **Automate the Kafka validation steps.** `docs/TEST_PLAN.md` §4 is entirely manual today; it's the biggest single gap relative to the project's own architectural emphasis on event-driven reliability (DLQ, retries).
2. **Write a QA document suite for the AI Copilot**, mirroring the chatbot's own five-document pattern (Test Plan / Test Cases / API Test / SQL Validation / Regression), since the underlying code already exists and is tested — this would convert already-proven code into audit-ready documentation, which is comparatively low effort for high payoff.
3. **Build an RTM** once a canonical requirements list exists for the V1 platform (today only V2's chatbot has formal BR-01/US-01 documents; V1's requirements live implicitly in `docs/architecture/00_Architecture_Understanding_v1.0.md` and the module list in the project description).
4. **Read `app/routes/`/`app/services/` for the untested modules** (restaurant, menu, kitchen-as-its-own-module, payment, delivery, notification, audit, DLQ) before writing their test cases, so those cases assert real behavior rather than assumed behavior — flagged rather than done in this pass, per your "do not modify/inspect deep into application source beyond what's needed for documentation" framing.
5. **Formalize the smoke suite** in `TC-GAP-01` §2 as an actual `pytest.mark.smoke` marker or `tests/smoke/` package, so "is the stack alive" stops being an implicit judgment call.
6. **File real defects** using `DEFECT_REPORT_TEMPLATE.md` for the bugs already fixed and narratively documented in `docs/governance/CHANGE-MANAGEMENT.md` (e.g. CHG-0015's validation-error-500 bug, CHG-0017's "typing disappears" bug) — right now they exist only as prose in the change log, not as structured defect records, so there's no queryable defect history.
