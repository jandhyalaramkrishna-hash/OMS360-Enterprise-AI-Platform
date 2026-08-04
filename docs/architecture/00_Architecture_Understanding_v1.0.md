# OMS-360 — Architecture Understanding (Baseline for AI Enhancement)
Version: v1.0 | Source: OMS360_v1.2_Production_Release.zip (uploaded 2026-07-18)

This document is the "ground truth" I extracted directly from your codebase
(not assumed). Every AI feature in this program will be checked against
this file so nothing contradicts the real system. Please correct anything
below before we design Feature 1.

---

## 1. Tech Stack (as-built)
- **Backend:** FastAPI + SQLAlchemy 2.0 (ORM), Pydantic v2 schemas, PyMySQL driver
- **DB:** MySQL 8 (`oms360_db`) — schema is `oms360_schema.sql` + 2 additive migrations
- **Messaging:** Kafka via `confluent-kafka`, one producer (`app/messaging/producer.py`),
  one consumer/orchestrator (`app/messaging/consumer.py`)
- **Layered service architecture:** routes → services → ORM. Routes do NOT touch
  tables directly (except a few dashboard read-only aggregation queries, by design).
- **Dashboards:** 2 static HTML files (Operations Center, Monitoring Center),
  vanilla JS polling every 6s — no frontend framework/build step.
- **Auth:** **None currently implemented.** No login, no JWT, no RBAC. This
  matters for every AI feature — any "user role" below is a *conceptual*
  actor in the business flow, not an enforced system role yet.
- **Containerization:** Docker Compose (mysql, zookeeper, kafka, api, consumer)

## 2. Business Flow (order lifecycle, as implemented)
```
Customer places order (POST /api/v1/orders)
  → validate payload + lock/reserve stock (inventory_service)
  → insert orders_master + order_items + transactions (one atomic commit)
  → write order_audit_trail (ORDER_CREATED)
  → publish Kafka: order.created
  → [async, consumer.py orchestrates:]
       payment_service.mark_payment_successful()  → payment_status = PAID
       kitchen_service starts cooking             → order_status = PREPARING
       kitchen finishes                            → order_status = READY
       delivery_service dispatches                 → order_status = OUT_FOR_DELIVERY
       delivery completes                           → order_status = DELIVERED
  → each stage writes order_audit_trail + publishes its Kafka topic
Failure paths: DuplicateOrderException → duplicate_orders table,
InsufficientStock/UnknownItem → 4xx, processing failure → retry → dlq_orders
```

## 3. Conceptual User Roles (business actors, not enforced auth roles)
| Role | Interacts via |
|---|---|
| Customer | `POST/GET /api/v1/orders` |
| Kitchen Staff / Chef | `kitchen_status` rows, Operations dashboard |
| Delivery Partner | `delivery_status` rows, Operations dashboard |
| Ops/Support Team | Operations Center dashboard, Alerts |
| Engineering/SRE | Monitoring Center dashboard, `/health`, `/metrics`, DLQ |
| Inventory Manager | `app/routes/inventory.py` (`/low-stock`, `/restock`, etc.) |

## 4. Core Database Tables (existing — I will reuse these, not duplicate them)
| Table | Purpose | Notably reusable columns for AI |
|---|---|---|
| `orders_master` | One row per order | `fraud_status` (CLEAR/SUSPECTED/BLOCKED) — **already exists, currently unused by any logic**; `live_window_track` |
| `order_items` | Line items per order | item_id, quantity, price |
| `transactions` | Payment transaction record | payment_status, amount |
| `kitchen_status` | Per-item cooking state | chef_name, cooking_status, started_at |
| `delivery_status` | Per-order delivery state | delivery_person, status |
| `inventory` / `items` | Stock levels | remaining_stock, status |
| `inventory_alerts` | Low/out-of-stock alerts | already written automatically |
| `inventory_ledger` | Stock movement history (migration 003) | RESTOCK/RESERVE/RELEASE/ADJUSTMENT |
| `order_audit_trail` | Full state-transition history (migration 002) | event_type, event_details, created_at |
| `duplicate_orders` | Detected duplicate requests | order_id, transaction_id, detected_at |
| `failed_orders` | Failed order log | reason, failed_at |
| `dlq_orders` | Kafka dead-letter queue | payload, moved_at |
| `system_configuration` | Key-value app config | reusable for AI feature toggles/thresholds |

## 5. Kafka Topics (existing — `app/core/enums.py::KafkaTopics`)
`order.created`, `payment.completed`, `payment.failed`, `kitchen.accepted`,
`kitchen.rejected`, `delivery.assigned`, `delivery.completed`,
`inventory.updated`, `notification.sent`, `order.dlq`, `order.retry`

## 6. Existing REST Endpoints (relevant surface)
- `POST/GET /api/v1/orders`, `GET /api/v1/orders/{id}`, `GET /api/v1/orders/{id}/audit`
- `GET /api/v1/inventory`, `/low-stock`, `/out-of-stock`, `/alerts`, `/history`, `POST /restock`
- `GET /api/v1/dashboard/kpis|live-orders|kitchen-ops|delivery-ops|alerts|monitoring|operations|analytics`
- `GET /health`, `GET /metrics`, `GET /version`

## 7. Important discovery — this codebase is already AI-ready by design
Two things your engineering team already put in place, deliberately, before
this conversation:
1. **`app/config.py`** already has an `ai_features_enabled` feature flag
   (currently `False`) plus `AI_PROVIDER` / `AI_MODEL_NAME` / `AI_API_KEY`
   placeholders, explicitly commented as **"V2 scope."**
2. **`orders_master.fraud_status`** (`CLEAR` / `SUSPECTED` / `BLOCKED`) and
   the **`FraudStatus` enum** already exist in the schema and codebase —
   but no service currently *sets* this column to anything other than the
   default `CLEAR`. It's a placeholder waiting for real fraud logic.

This means: our AI features are not being bolted onto a system that never
anticipated them — we are switching on capability the schema already has
slots for. This is a strong, honest talking point for interviews.

## 8. Design Constraints for Every AI Feature Going Forward
- Reuse existing tables/columns wherever possible (see Section 4). New
  columns/tables only when a real gap exists, and always additive
  (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN`), never
  destructive.
- New AI logic lives in **new service files** (e.g. `ai_fraud_service.py`)
  called from existing routes/consumer — never inline business logic
  changes to `order_service.py`'s core flow.
- Every AI call is **gated behind `FEATURE_FLAGS["ai_features_enabled"]`**
  (already defined) plus a per-feature sub-flag, so AI can be toggled off
  instantly without a redeploy if it misbehaves.
- Every AI feature must degrade gracefully — if the LLM/model call fails
  or times out, the existing non-AI business flow must complete unaffected
  (AI is advisory/additive, never a blocking dependency of order fulfillment).
- Every AI feature gets its own Kafka topic (`ai.*` namespace) only if
  genuinely event-driven; otherwise it's a synchronous service call — we
  won't invent Kafka events for the sake of it.

## 9. Versioning Plan
- **OMS360 AI Enterprise v1.0** = this document + folder scaffold (today)
- **v1.1** = Feature 1 (first AI feature, full spec + QA + interview prep)
- **v1.2** = Feature 2 ... and so on, one minor version per feature
- Each version is zipped and preserved; nothing is overwritten.

---
*Next step: confirm this understanding, then we design Feature 1 in full
depth before moving to Feature 2.*
