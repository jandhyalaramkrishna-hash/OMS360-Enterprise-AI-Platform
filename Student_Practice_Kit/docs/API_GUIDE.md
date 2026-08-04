# OMS360 Enterprise AI Platform — API Guide (Student Practice Edition)

**Developed by ZelQA Technologies**

Once the app is running, the interactive Swagger docs at `/docs` are the
best way to explore and try every endpoint live — this guide is a map to
help you navigate them, not a replacement. All paths below are relative to
the local address shown in the status window (typically
`http://127.0.0.1:8000`).

This is the real OMS360 API — every endpoint listed here is backed by the
actual, unmodified application code, not a mock or simplified copy.

## Interactive docs

| URL | What it is |
|---|---|
| `/docs` | Swagger UI — try every endpoint directly from the browser |
| `/redoc` | Alternative read-only API reference (if enabled) |
| `/dashboard/operations` | Operations Center dashboard (HTML) |
| `/dashboard/monitoring` | Monitoring Center dashboard (HTML) |

## System endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Root ping — confirms the API is reachable |
| GET | `/version` | Application version info |
| GET | `/health` | Full health check: database, Kafka broker/producer, disk, memory, CPU. In this edition, Kafka reports `"status": "DISABLED"` — that's expected, see `STUDENT_GUIDE.md` §5. |
| GET | `/metrics` | In-memory + database-backed operational metrics (orders processed/failed, API timings, DLQ summary, etc.) |

## Orders — `/api/v1/orders`

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/orders` | Create a new order. Validates stock, locks inventory, records the order + items + a transaction, writes an audit trail entry — all in one atomic transaction. Send an `Idempotency-Key` header to make retries safe: the same key within the TTL window returns `409` instead of creating a duplicate order. |
| GET | `/api/v1/orders?limit=50` | List recent orders |
| GET | `/api/v1/orders/{order_id}` | Get one order (with items) |
| GET | `/api/v1/orders/{order_id}/audit` | Full state-transition history for an order (oldest first) |

**Sample create-order request body** (also in `sample-data/create_order_request.json`):

```json
{
  "customer_id": "CUST-001",
  "customer_name": "Anil Kumar",
  "mobile": "9876543210",
  "payment_method": "UPI",
  "enterprise_id": "ENT-99",
  "items": [{ "item_id": "ITEM-BURGER", "quantity": 2 }],
  "delivery_address": {
    "door_no": "12/B",
    "street": "M G Road",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001"
  }
}
```

Validation rules worth practicing against: `mobile` must be exactly 10
digits starting with 6–9; `pincode` must be exactly 6 digits; `quantity`
must be a positive integer; name/address fields cannot be blank. Try
sending invalid values and observe the `422` responses — this is a good,
safe way to practice negative testing.

## Inventory — `/api/v1/inventory`

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/inventory` | List all inventory items |
| GET | `/api/v1/inventory/low-stock` | Items below their reorder threshold |
| GET | `/api/v1/inventory/out-of-stock` | Items with zero stock |
| GET | `/api/v1/inventory/alerts?limit=50` | Recent inventory alerts |
| GET | `/api/v1/inventory/history?item_id=...&limit=100` | Stock ledger history (optionally filtered to one item) |
| GET | `/api/v1/inventory/{item_id}` | One inventory item |
| POST | `/api/v1/inventory/restock` | Restock an item |
| PUT | `/api/v1/inventory/{item_id}` | Update an inventory item |

## Dashboards — `/api/v1/dashboard`

These return JSON (used by the HTML dashboards above, and useful directly
for API testing):

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/dashboard/operations` | Operations summary |
| GET | `/api/v1/dashboard/analytics` | Analytics summary |
| GET | `/api/v1/dashboard/kpis` | Bottom KPI bar |
| GET | `/api/v1/dashboard/live-orders?limit=25` | Live orders feed |
| GET | `/api/v1/dashboard/kitchen-ops?limit=25` | Kitchen operations feed |
| GET | `/api/v1/dashboard/delivery-ops?limit=25` | Delivery operations feed |
| GET | `/api/v1/dashboard/alerts?limit=30` | Business alerts feed |
| GET | `/api/v1/dashboard/monitoring` | Full monitoring snapshot |

## AI platform — `/api/v1/ai`

The AI modules are real, deterministic, mock-based implementations (no
external AI vendor is called) — a good sandbox to practice testing
health/status/config-style endpoints.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/ai/health` | AI subsystem health |
| GET | `/api/v1/ai/config` | Current AI runtime configuration |
| GET | `/api/v1/ai/providers` | Configured AI provider(s) |
| GET | `/api/v1/ai/features` | Feature flags |
| GET | `/api/v1/ai/metrics` | AI metrics snapshot |
| GET | `/api/v1/ai/status` | Overall AI service status |
| GET | `/api/v1/ai/platform/health` | Unified health report across every AI module (agents, RAG, MCP, evaluation, providers) |

## Error format

Every error response follows the same envelope:

```json
{ "error": "<short_code>", "detail": "<message>", "request_id": "<id>" }
```

Validation errors (`422`) additionally include a `fields` array with
per-field details. Practicing against this consistent shape is a good way
to write reusable API test assertions.

---
OMS360 Enterprise AI Platform — Developed by ZelQA Technologies
