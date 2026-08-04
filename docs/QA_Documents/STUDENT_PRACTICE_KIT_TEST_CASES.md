<!-- Consolidated into docs/QA_Documents/ on 2026-08-03. Original remains at Student_Practice_Kit/docs/TEST_CASES.md (must stay there — it ships as part of the distributed practice kit). Renamed on copy only, to avoid colliding with docs/TEST_PLAN.md's own test cases in this shared folder. Sections B/C/D overlap ~60-70% with docs/TEST_PLAN.md's FUNC/API/NEG sections (same underlying API); Sections A and F (Licensing, Evaluation Expiry) are unique to the packaged distribution and have no equivalent elsewhere. Content below is an exact copy, unmodified. -->

# OMS360 Enterprise AI Platform — Starter QA Test Case Suite

**Developed by ZelQA Technologies** · Student Practice Edition

A starter set of manual test cases to practice with. Use these as a
template — write more of your own as you explore. Record your actual
results and file a defect (see `DEFECT_REPORT_TEMPLATE.md`) for anything
that doesn't match the expected result.

Legend: **Pre** = precondition, **Steps**, **Expected**.

## A. Licensing & Activation

| ID | Title | Pre | Steps | Expected |
|---|---|---|---|---|
| LIC-01 | First-launch activation prompt | Fresh install, never activated | Double-click the exe | Splash appears, then an Activation window asking for a License Key |
| LIC-02 | Successful activation with a valid key | Have a real key from your instructor | Paste the key, click Activate | Activation succeeds; app starts; status window shows "Licensed Student: <you>" and "Days Remaining: 7 days" |
| LIC-03 | Rejects an invalid/made-up key | App running, activation window open | Enter `ZELQA-OMS360-NOTAREALKEY` and click Activate | A clear error message appears; app does not start |
| LIC-04 | No re-prompt on second launch | Already activated once | Stop the app, double-click the exe again | App starts directly to the splash/status window — no activation prompt |
| LIC-05 | Days Remaining counts down | Activated | Check "Days Remaining" on day 1 vs. a later day | Value decreases day over day, never increases |

## B. Order Creation (Happy Path)

| ID | Title | Pre | Steps | Expected |
|---|---|---|---|---|
| ORD-01 | Create a valid order | App running | `POST /api/v1/orders` with `sample-data/create_order_request.json` | `201 Created`; response includes `order_id`, items, and a `RECEIVED` status |
| ORD-02 | Retrieve the created order | ORD-01 done | `GET /api/v1/orders/{order_id}` | Returns the same order with matching items |
| ORD-03 | Order appears in the list | ORD-01 done | `GET /api/v1/orders` | The new order is present in the response |
| ORD-04 | Audit trail recorded | ORD-01 done | `GET /api/v1/orders/{order_id}/audit` | At least one entry (order creation) is present |
| ORD-05 | Order appears on the Operations Dashboard | ORD-01 done | Open `/dashboard/operations` in a browser | The order shows up in the live feed |

## C. Order Creation (Negative / Validation)

| ID | Title | Steps | Expected |
|---|---|---|---|
| ORD-NEG-01 | Invalid mobile number | `POST /api/v1/orders` with `mobile: "12345"` | `422`, error mentions mobile must be 10 digits starting 6–9 |
| ORD-NEG-02 | Invalid pincode | Same as above but with `pincode: "12"` | `422`, error mentions pincode must be 6 digits |
| ORD-NEG-03 | Unknown item | `item_id` that doesn't exist in inventory | `400` or `409` with a clear error (not a 500) |
| ORD-NEG-04 | Insufficient stock | Order a quantity larger than available stock | `409 Conflict` |
| ORD-NEG-05 | Blank customer name | `customer_name: ""` | `422` |
| ORD-NEG-06 | Duplicate request with Idempotency-Key | Repeat ORD-01's exact request with the same `Idempotency-Key` header within the TTL window | Second request returns `409`, no second order is created |

## D. Inventory

| ID | Title | Steps | Expected |
|---|---|---|---|
| INV-01 | List all inventory | `GET /api/v1/inventory` | Returns a list of items with quantities |
| INV-02 | Low-stock list is a subset of full inventory | `GET /api/v1/inventory/low-stock` | Every item returned also appears in `GET /api/v1/inventory`, and is below its threshold |
| INV-03 | Restock decreases "low stock" status | Restock a low-stock item via `POST /api/v1/inventory/restock` | Item no longer appears in `/low-stock` (if now above threshold) |
| INV-04 | Restocking after an order reflects the deduction | Create an order (ORD-01), then check `GET /api/v1/inventory/{item_id}` | Quantity has decreased by the ordered amount |
| INV-05 | History reflects both the order and the restock | `GET /api/v1/inventory/history?item_id=...` | Ledger entries for both the deduction and the restock appear, oldest first |

## E. Health, Metrics & AI Platform

| ID | Title | Steps | Expected |
|---|---|---|---|
| SYS-01 | Root ping | `GET /` | `200 OK` |
| SYS-02 | Health check reports Kafka as disabled, not broken | `GET /health` | `200 OK`; Kafka section shows `"status": "DISABLED"` (expected in this edition — not a defect) |
| SYS-03 | Metrics endpoint returns a snapshot | `GET /metrics` | `200 OK`; includes order counters and a `dlq` section |
| SYS-04 | AI platform unified health | `GET /api/v1/ai/platform/health` | `200 OK`; reports every AI module (agents, RAG, MCP, evaluation, providers) |

## F. Evaluation Expiry (do this last, deliberately, near the end of your practice)

| ID | Title | Steps | Expected |
|---|---|---|---|
| EXP-01 | App reports remaining time accurately | Check "Days Remaining" against how many days have actually passed since your first activation | Matches (± rounding to whole days) |
| EXP-02 | Expired evaluation blocks startup | After your 7-day period has actually ended, double-click the exe | "Evaluation Expired. Please contact ZelQA Technologies." is shown; app exits without starting |

---
OMS360 Enterprise AI Platform — Developed by ZelQA Technologies
