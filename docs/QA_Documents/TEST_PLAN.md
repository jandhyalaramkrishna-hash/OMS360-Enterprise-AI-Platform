<!-- Consolidated into docs/QA_Documents/ on 2026-08-03. Original remains at docs/TEST_PLAN.md. Scope: V1 — the live OMS-360 business platform (app/). Distinct from TP-01-AI-Customer-Support-Chatbot_v1.1.md, which covers the unbuilt V2 chatbot. Content below is an exact copy, unmodified. -->

# OMS-360 — Test Plan (Version 1.0)

Scope: `app/` (the authoritative FastAPI service). `api_gateway.py` and the
curses dashboards are legacy/demo code and are out of scope for this plan.

## 1. Functional Test Cases

| ID | Case | Expected Result |
|---|---|---|
| FUNC-01 | Place an order with valid items and address | 201, order_status=RECEIVED, stock decremented |
| FUNC-02 | Place an order with multiple line items | All items inserted into order_items, grand_total = sum(price*qty) |
| FUNC-03 | Kafka consumer picks up order.created | kitchen_status moves QUEUED→COOKING→READY, delivery_status moves PENDING→OUT_FOR_DELIVERY→DELIVERED |
| FUNC-04 | Full order lifecycle | orders_master.order_status ends as DELIVERED, payment_status ends as PAID |
| FUNC-05 | Retrieve order by ID | GET /api/v1/orders/{id} returns order + items |
| FUNC-06 | Retrieve order audit trail | GET /api/v1/orders/{id}/audit returns events in chronological order, includes ORDER_CREATED and INVENTORY_RESERVED at minimum |
| FUNC-07 | List inventory | GET /api/v1/inventory returns all items with current stock |

## 2. API Test Cases

| ID | Endpoint | Case | Expected |
|---|---|---|---|
| API-01 | POST /api/v1/orders | Unknown item_id | 400, error=unknown_item |
| API-02 | POST /api/v1/orders | Quantity > available stock | 409, error=insufficient_stock |
| API-03 | POST /api/v1/orders | Same Idempotency-Key twice | 2nd call returns 409, error=duplicate_order |
| API-04 | POST /api/v1/orders | Invalid mobile (e.g. "123") | 422, validation_error, field-level detail |
| API-05 | POST /api/v1/orders | Invalid pincode (e.g. "12A456") | 422, validation_error |
| API-06 | POST /api/v1/orders | Missing required field (e.g. no customer_name) | 422, validation_error |
| API-07 | GET /api/v1/orders/{id} | Nonexistent order_id | 404 |
| API-08 | GET /health | — | 200, dependencies for database/kafka/application/disk/memory all present |
| API-09 | GET /metrics | — | 200, counters + api_response_times + kafka_processing_time_ms present |
| API-10 | Any endpoint | Trigger an unexpected exception | 500, generic message, request_id present, NO stack trace in response body |
| API-11 | Any endpoint | Check response headers | X-Request-ID present on every response |

Postman: import the OpenAPI schema directly from `/openapi.json` (Swagger UI
at `/docs` also lets you "Try it out" against a running instance) — every
endpoint already has descriptions and example bodies per the schemas in
`app/schemas.py`.

## 3. SQL Validation Queries

Run these after a test order (`{order_id}`) to confirm end-to-end
persistence — automated versions of these live in `tests/test_sql_validation.py`.

```sql
SELECT * FROM orders_master WHERE order_id = '{order_id}';
SELECT * FROM order_items WHERE order_id = '{order_id}';
SELECT * FROM kitchen_status WHERE order_id = '{order_id}';
SELECT * FROM delivery_status WHERE order_id = '{order_id}';
SELECT * FROM transactions WHERE order_id = '{order_id}';
SELECT * FROM order_audit_trail WHERE order_id = '{order_id}' ORDER BY created_at ASC;

-- Stock should have decremented by exactly the ordered quantity:
SELECT item_id, remaining_stock, used_stock FROM inventory WHERE item_id = '{item_id}';

-- Rollback check: an order that failed validation should leave NO rows here:
SELECT * FROM order_items WHERE order_id = '{order_id_of_failed_order}';

-- Duplicate detection check:
SELECT * FROM duplicate_orders WHERE transaction_id = '{idempotency_key}';

-- DLQ check (after simulating a Kafka outage - see Section 4):
SELECT * FROM dlq_orders ORDER BY moved_at DESC LIMIT 5;
```

## 4. Kafka Validation Steps

| Step | Action | Expected |
|---|---|---|
| KAFKA-01 | Place an order with the consumer running | Consumer logs `STAGE=KITCHEN_STARTED` then `STAGE=KITCHEN_COMPLETED` then `STAGE=OUT_FOR_DELIVERY` then `STAGE=DELIVERED` for that order_id |
| KAFKA-02 | Place an order with the consumer stopped | order.created is published (check with a `kafka-console-consumer` on `order.created`); kitchen/delivery stay at QUEUED/PENDING until consumer restarts and catches up |
| KAFKA-03 | Stop the Kafka broker, place an order | API still returns 201 (publish is best-effort); after MAX_RETRY_COUNT attempts, a row appears in `dlq_orders` with the order.created payload |
| KAFKA-04 | Restart Kafka after KAFKA-03 | No automatic re-delivery from dlq_orders (by design — it's a table, not a topic being re-consumed); confirms the "don't retry forever" requirement |
| KAFKA-05 | Check topic list | `docker exec oms360_kafka kafka-topics --bootstrap-server localhost:9092 --list` should show order.created, kitchen.accepted, delivery.assigned, delivery.completed at minimum, once at least one order has flowed through |

## 5. Negative Test Scenarios

| ID | Scenario | Expected |
|---|---|---|
| NEG-01 | Order with 0 or negative quantity | 422 (Pydantic `gt=0` on quantity) |
| NEG-02 | Order with empty items list | 422 (`min_length=1` on items) |
| NEG-03 | Two orders racing for the last unit of stock | Exactly one succeeds (201), the other gets 409 insufficient_stock — proven by `with_for_update()` row locking in order_service.py |
| NEG-04 | Malformed JSON body | 422/400 from FastAPI's own body parsing, consistent error shape |
| NEG-05 | Database unreachable | POST /api/v1/orders returns 500 with generic message; GET /health reports database=DOWN with the real error; no stack trace leaks to the client |
| NEG-06 | Kafka unreachable at startup | API still starts and serves requests; GET /health reports kafka=DOWN |
| NEG-07 | Consumer crashes mid-order (e.g. killed during cooking simulation) | kitchen_status is left at COOKING (not stuck at QUEUED, not falsely READY) — acceptable for a demo; a production system would need a saga/outbox pattern here, out of scope for V1 |

## 6. Out of Scope for V1 (see Future Scope, Version 2.0)

AI Test Assistant, AI Report Summarization, AI Test Case Generation,
Predictive Analytics, Intelligent Monitoring.
