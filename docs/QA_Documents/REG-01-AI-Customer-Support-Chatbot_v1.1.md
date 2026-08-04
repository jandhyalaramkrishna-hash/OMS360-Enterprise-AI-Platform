<!-- Consolidated into docs/QA_Documents/ on 2026-08-03. Original remains at docs/qa/REG-01-AI-Customer-Support-Chatbot_v1.1.md. Scope: V2 AI Customer Support Chatbot (documentation-only, not yet built). Content below is an exact copy, unmodified. -->

# Regression Testing — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

## Why Regression Risk Is Low Here (and how to prove it)
This feature adds new files/tables/endpoints/one Kafka topic. It does
not modify `order_service.py`, `consumer.py`, `producer.py`,
`inventory_service.py`, `payment_service.py`, `kitchen_service.py`,
`delivery_service.py`, or any existing route file's existing handlers.
Regression testing exists to *prove* that claim, not assume it.

## Regression Checklist
| # | Check | Method | Expected |
|---|---|---|---|
| 1 | Full existing automated suite passes unchanged | Run `pytest tests/` with feature flag OFF | All existing tests (`test_health.py`, `test_orders.py`, `test_sql_validation.py`) pass, same as pre-feature baseline |
| 2 | Full existing automated suite passes with flag ON | Run `pytest tests/` with `ai_chatbot_enabled=true` | Identical results to #1 — proves the feature doesn't leak side effects into unrelated flows even when active |
| 3 | Order creation → fulfillment lifecycle unaffected | Create a real order via `POST /api/v1/orders`, let it flow through the consumer to DELIVERED | Same state transitions, same audit trail entries, same timing as before this feature existed |
| 4 | Existing dashboard endpoints unchanged in shape | Diff JSON response shape of `/kpis`, `/live-orders`, `/kitchen-ops`, `/delivery-ops`, `/alerts`, `/monitoring`, `/operations`, `/analytics` before/after | No new required fields, no removed fields, no type changes |
| 5 | Existing Kafka topics unaffected | Monitor `order.created`...`inventory.updated` during a chatbot load test | No unexpected messages, no consumer lag increase attributable to chatbot activity |
| 6 | Inventory module unaffected | Run existing inventory test scenarios (`/low-stock`, `/restock`, etc.) | Behavior identical |
| 7 | Health/metrics endpoints still report correctly | `GET /health`, `GET /metrics` | Now optionally include one new AI-health sub-section (additive field only), all existing fields unchanged |
| 8 | DB migration is idempotent | Run `migrations/004_add_ai_chatbot_tables.sql` twice | Second run is a no-op (`IF NOT EXISTS`), no error |
| 9 | Feature flag OFF leaves zero footprint on request latency | Load test existing `POST /api/v1/orders` with chatbot code deployed but flag off | Latency within normal existing baseline (no measurable overhead from dead code path) |
| 10 | No new required environment variable breaks existing deployments | Boot the app with `.env` from before this feature existed (no `AI_*` vars set) | App boots successfully; `ai_chatbot_enabled` defaults to false; no crash on missing `AI_API_KEY` |

## Sign-off Criteria
Regression pass = all 10 checks green, on both flag states (ON/OFF),
before this feature can move from "Design Complete" to "Approved for
Build."
