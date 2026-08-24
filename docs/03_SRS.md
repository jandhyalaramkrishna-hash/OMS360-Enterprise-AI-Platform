# 03 — Software Requirements Specification (SRS)

**Project:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform
**Last consolidated:** 2026-08-04 (documentation reorganization — renumbered from `docs/SRS.md`, content unchanged)

Canonical System Requirements Specification, consolidated from
`docs/architecture/00_Architecture_Understanding_v1.0.md`,
`docs/architecture/Feature-01-AI-Customer-Support-Chatbot_v1.1.md`,
`docs/architecture/API-01-...md`, `docs/architecture/DB-01-...md`,
`docs/architecture/KAFKA-01-...md`, and README.md. Traces to the business
requirements in `docs/02_BRS.md`. Source documents are left in place for full
V2-level detail (not duplicates — each is a distinct, detailed spec this
SRS summarizes); this file is the single starting point.

---

## 1. System Overview

OMS-360 is an event-driven food-delivery order management platform.
Requests enter through a **layered architecture — routes → services → ORM**
(routes do not touch tables directly, except a few read-only dashboard
aggregation queries, by design). State changes are propagated
asynchronously via **Apache Kafka**, persisted in **MySQL 8**, and exposed
through a **FastAPI** REST API with auto-generated OpenAPI/Swagger docs.
The whole stack runs under **Docker Compose**.

### 1.1 Tech Stack (as-built, V1)

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 (ORM) + Pydantic v2 schemas + PyMySQL driver |
| Database | MySQL 8 (`oms360_db`) — `oms360_schema.sql` + additive migrations (`002_add_audit_trail.sql`, `003_add_inventory_ledger.sql`) |
| Messaging | Kafka via `confluent-kafka` — one producer (`app/messaging/producer.py`), one consumer/orchestrator (`app/messaging/consumer.py`) |
| Dashboards | Static HTML (Operations Center, Monitoring Center, Inventory, AI Copilot) — vanilla JS, 6s polling, no frontend framework/build step |
| Containerization | Docker Compose — `mysql`, `zookeeper`, `kafka`, `api` (`oms360_core_engine`), `consumer` (`oms360_consumer`) |
| AI layer | `ai/` — Provider Framework, RAG, MCP, Multi-Agent, Evaluation, Enterprise Integration (all mock-based) |
| Auth | **None implemented.** No login, no JWT, no RBAC — a documented, known gap, not an oversight |

### 1.2 System Boundary

In scope: the FastAPI service, its Kafka producer/consumer, MySQL
persistence, the four static dashboards, the `ai/` platform layer, and the
QA tooling that verifies all of the above (Newman/Postman, pytest/Allure,
Jenkins, Playwright). Out of scope: any external customer-facing mobile/web
app (not present in this repository — this repo delivers the API only),
any real payment gateway, any real SMS/email provider, any real LLM vendor.

---

## 2. Functional Requirements — V1 Business Platform

### 2.1 Order Lifecycle (primary flow)

```
POST /api/v1/orders
  -> validate payload + lock/reserve stock (inventory_service, row-level locking)
  -> insert orders_master + order_items + transactions (one atomic commit)
  -> write order_audit_trail (ORDER_CREATED)
  -> publish Kafka: order.created
  -> [async, consumer.py orchestrates:]
       payment_service.mark_payment_successful()  -> payment_status = PAID
       kitchen_service starts cooking             -> order_status = PREPARING
       kitchen finishes                            -> order_status = READY
       delivery_service dispatches                 -> order_status = OUT_FOR_DELIVERY
       delivery completes                           -> order_status = DELIVERED
  -> each stage writes order_audit_trail + publishes its own Kafka topic
```

Failure paths: `DuplicateOrderException` -> `duplicate_orders` table;
`InsufficientStock`/`UnknownItem` -> 4xx; processing failure -> retry ->
`dlq_orders`.

### 2.2 Functional Requirement Table

| ID | Requirement | Verified by |
|---|---|---|
| FR-01 | System shall accept a new order with valid items/address and reserve stock atomically | `docs/07_Test_Plan.md` FUNC-01, Newman "02 Orders" folder |
| FR-02 | System shall support multi-line-item orders with a correctly summed grand total | FUNC-02 |
| FR-03 | System shall advance an order through kitchen and delivery status via Kafka, asynchronously | FUNC-03, KAFKA-01…05 |
| FR-04 | System shall reach a terminal `DELIVERED`/`PAID` state for a valid order with no manual intervention | FUNC-04 |
| FR-05 | System shall expose order retrieval by ID | FUNC-05 |
| FR-06 | System shall expose a full chronological audit trail per order | FUNC-06 |
| FR-07 | System shall expose current inventory levels | FUNC-07 |
| FR-08 | System shall reject duplicate order submissions (idempotency key) | API-03 |
| FR-09 | System shall resolve concurrent stock races correctly (exactly one winner) | NEG-03 |
| FR-10 | System shall route unprocessable Kafka events to a dead-letter queue after `MAX_RETRY_COUNT` | KAFKA-03/04 |
| FR-11 | System shall serve live operational dashboards (Operations, Monitoring, Inventory, AI Copilot) refreshed every 6s | `docs/15_Installation_Guide.md` §7, TC-GAP-01 DASH-01…06 |

### 2.3 Core Database Entities (existing, reused — not duplicated by any new feature)

| Table | Purpose |
|---|---|
| `orders_master` | One row per order (includes `fraud_status` — schema slot reserved, not yet driven by real logic) |
| `order_items` | Line items per order |
| `transactions` | Payment transaction record |
| `kitchen_status` | Per-item cooking state |
| `delivery_status` | Per-order delivery state |
| `inventory` / `items` | Stock levels |
| `inventory_alerts` | Low/out-of-stock alerts |
| `inventory_ledger` | Stock movement history (migration 003) |
| `order_audit_trail` | Full state-transition history (migration 002) |
| `duplicate_orders` | Detected duplicate requests |
| `failed_orders` | Failed order log |
| `dlq_orders` | Kafka dead-letter queue |
| `system_configuration` | Key-value app config |

### 2.4 Kafka Topics

`order.created`, `payment.completed`, `payment.failed`,
`kitchen.accepted`, `kitchen.rejected`, `delivery.assigned`,
`delivery.completed`, `inventory.updated`, `notification.sent`,
`order.dlq`, `order.retry` — defined in `app/core/enums.py::KafkaTopics`.

### 2.5 REST API Surface (relevant, real endpoints)

`POST/GET /api/v1/orders`, `GET /api/v1/orders/{id}`,
`GET /api/v1/orders/{id}/audit`, `GET /api/v1/inventory` (+
`/low-stock`, `/out-of-stock`, `/alerts`, `/history`, `POST /restock`),
`GET /api/v1/dashboard/{kpis|live-orders|kitchen-ops|delivery-ops|alerts|monitoring|operations|analytics}`,
`GET /health`, `GET /metrics`, `GET /version`, plus the AI Runtime/Copilot
surface under `/api/v1/ai/*`. Full request/response contracts: `/openapi.json`
(Swagger UI at `/docs`), and the real 56-request Postman collection at
`postman/collection/OMS360.postman_collection.json` (see `docs/09_API_Test_Cases.md`).

---

## 3. Non-Functional Requirements

| ID | Category | Requirement | Source |
|---|---|---|---|
| NFR-01 | Reliability | Every module must have automated test coverage before being marked Complete | `docs/06_Test_Strategy.md` §1 |
| NFR-02 | Reliability | Kafka publish failures must retry then fall back to a DLQ, never silently drop | Architecture §2, KAFKA-03 |
| NFR-03 | Observability | `/health` returns HTTP 200 always; overall status is in the JSON `status` field, degraded dependencies are visible, not hidden behind a non-200 | `docs/FINAL_RELEASE_REPORT.md` §2.1 |
| NFR-04 | Observability | `/metrics` exposes counters, API response times, Kafka processing time | API-09 |
| NFR-05 | Security | All input validated via Pydantic (types/constraints); parameterized queries only, no raw SQL from user input | `docs/06_Test_Strategy.md` §8 |
| NFR-06 | Security | No stack trace ever leaks to a client on an unhandled 500 | API-10 |
| NFR-07 | Performance | Baseline load test per module before it's marked Complete; Kafka consumer lag monitored under load | `docs/06_Test_Strategy.md` §7 |
| NFR-08 | Logging | Every key state transition emits a structured log entry with a correlation/order ID; no sensitive data logged | `docs/06_Test_Strategy.md` §6 |
| NFR-09 | Idempotency | Repeated requests with the same Idempotency-Key must not create duplicate orders | API-03 |
| NFR-10 | Portability | Full stack must run via `docker compose up` with no manual per-service setup beyond one manual migration (`003`, documented) | `docs/15_Installation_Guide.md` §1 |
| NFR-11 | AI additivity | Every AI feature must be gated behind a feature flag and degrade gracefully if the model/tool call fails — never a blocking dependency of order fulfillment | Architecture Understanding §8 |

---

## 4. V2 Chatbot — System-Level Spec (documented, not built)

Full detail: `docs/architecture/Feature-01-AI-Customer-Support-Chatbot_v1.1.md`
(functional flow, prompt design, hallucination mitigations),
`docs/architecture/API-01-...md` (4 new endpoints under `/api/v1/chatbot`
and one dashboard feed endpoint), `docs/architecture/DB-01-...md` (4 new,
fully additive tables — `ai_chatbot_conversations`, `ai_chatbot_messages`,
`ai_chatbot_escalations`, `ai_faq_knowledge_base`), `docs/architecture/KAFKA-01-...md`
(one new topic, `ai.chatbot.escalated`). Design pattern: **Retrieval-Augmented
+ tool/function calling**, never fine-tuning, never a raw-DB-dump prompt —
every factual claim must be backed by an actual tool call this turn
(the core anti-hallucination control). Not re-typed here in full; this SRS
records only that the spec exists, is complete, and is unbuilt.

---

## 5. External Interfaces

| Interface | Direction | Protocol |
|---|---|---|
| Customer-facing order placement | Inbound | REST/JSON over HTTP, `POST /api/v1/orders` |
| Kafka broker | Internal | `confluent-kafka` producer/consumer, `kafka:29092` in-network / `localhost:9092` external |
| MySQL | Internal | SQLAlchemy/PyMySQL, `mysql:3306` in-network / `localhost:3306` external |
| Operations/Monitoring/Inventory/AI-Copilot dashboards | Outbound | Server-rendered static HTML + polling JS (6s interval) |
| Swagger/OpenAPI | Outbound | `GET /docs`, `GET /openapi.json` |
| QA tooling (Newman, pytest, Allure, Jenkins) | External, verification-only | HTTP against the running API — never starts/stops the stack itself, see `docs/06_Test_Strategy.md` |

---

## 6. Traceability

See `docs/10_RTM.md` (companion spreadsheet: `docs/RTM.xlsx`) for the full
requirement -> test case mapping for every FR/NFR ID above.
