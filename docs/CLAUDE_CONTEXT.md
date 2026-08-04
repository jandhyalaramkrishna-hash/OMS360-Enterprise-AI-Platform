# CLAUDE_CONTEXT.md — OMS-360 Enterprise Dashboards

Read this file first in any future session before touching this project.
It exists so work can continue without re-discovering the codebase from
scratch or repeating design decisions that were already made deliberately.

---

## 1. Project Overview

OMS-360 is an existing enterprise Order Management System: FastAPI +
SQLAlchemy + MySQL, with Kafka for async order/kitchen/delivery event
flow. The backend (routes, models, services, messaging, migrations) was
already built and delivered before this session — it was NOT redesigned.

This session's job was to add **two enterprise HTML dashboards** on top of
the existing, unmodified architecture:

1. **OMS-360 Enterprise Operations Center** — business workflow view
   (live orders, kitchen, delivery, alerts, order lifecycle, KPI bar).
2. **OMS-360 Enterprise Monitoring Center** — technical/observability view
   (app/DB/Kafka/Docker health, DLQ, duplicate/failed orders, retry queue,
   inventory/Kafka/API summaries, performance, recent alerts).

Both dashboards use **only live data from the existing MySQL database via
new/existing FastAPI JSON endpoints** — no hardcoded/static business data.

## 2. Current Implementation Status

**Status: Feature-complete and code-reviewed. NOT yet run against a real
MySQL + Kafka stack** (see Section 9 — environment constraint). UI/UX was
verified visually with Playwright screenshots against a throwaway mock
JSON server that returns data shaped exactly like the real endpoints.

Everything below "Completed Work" is done. Everything under "Pending Work"
is what's left before this can be called fully production-verified.

## 3. Completed Work

- Read and mapped the entire existing codebase (models, schemas, routes,
  services, messaging, core, config, migrations, schema SQL) before
  writing anything.
- Added 6 new read-only JSON endpoints to `app/routes/dashboard.py`
  (see Section 7) — `/operations` and `/analytics` (pre-existing) were
  **not touched**.
- Added static-file serving + 2 HTML page routes to `app/main.py`
  (see Section 7) — no new pip dependency (no Jinja2; plain
  `FileResponse` + `StaticFiles`).
- Built `app/static/operations_dashboard.html` — Operations Center,
  single self-contained file (inline CSS + vanilla JS, no build step,
  no external JS framework).
- Built `app/static/monitoring_dashboard.html` — Monitoring Center, same
  approach.
- Both dashboards poll their JSON endpoints every 6 seconds
  (`setInterval`) and re-render in place — this is the "Auto Refresh"
  requirement. A connection-error banner appears if a fetch fails and the
  last good data stays on screen (no blank/broken UI on a transient
  network hiccup).
- Verified all modified/added Python files with `python3 -m py_compile`
  — all pass.
- Verified the embedded `<script>` blocks in both HTML files with
  `node --check` — both pass.
- Visually verified layout, dark theme, alignment, spacing, and
  responsiveness by rendering both dashboards with Playwright + Chromium
  against a mock JSON server (`verification/mock_api.py`, included in
  this ZIP — see Section 9) at desktop (1600px) and tablet (900px)
  viewports. Screenshots confirmed: no overlapping elements, correct
  KPI bar behavior (fixed to viewport bottom; it only *looks* misplaced
  in `full_page` Playwright screenshots because `position:fixed` gets
  frozen in place during full-page stitching — confirmed correct by
  scrolling a normal viewport screenshot instead).

## 4. Pending Work (for the next session)

1. **Run against the real stack.** This sandbox had no network access, so
   `fastapi`/`sqlalchemy`/`pymysql`/`confluent-kafka` could not be
   installed and no MySQL server could be started here. The next session
   (or you, locally) needs to:
   - `pip install -r requirements.txt`
   - Apply `oms360_schema.sql`, then `migrations/002_add_audit_trail.sql`,
     then `migrations/003_add_inventory_ledger.sql`
   - `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - Open `http://localhost:8000/dashboard/operations` and
     `http://localhost:8000/dashboard/monitoring`
   - Confirm `/health`, `/metrics`, and all `/api/v1/dashboard/*`
     endpoints return real data with no 500s.
2. **Load-test the 6-second polling** against a real dataset (hundreds/
   thousands of orders) — `live-orders`, `kitchen-ops`, `delivery-ops`
   all default to `limit=25` query params to keep payloads small; raise
   or paginate if needed.
3. **Optional:** wire real authentication before exposing these
   dashboards outside a trusted network — there is currently no auth on
   any route (matches the rest of the existing API, which also has none).
4. **Optional:** if you want true Kafka consumer lag (not just
   broker/topic visibility), that requires a live consumer instance —
   flagged as a known limitation in `app/core/kafka_admin.py` already,
   unchanged in this session.
5. Take final "official" screenshots against the real running stack once
   verified end-to-end (the ones in this ZIP are from the mock-data
   verification pass, not the live DB).

## 5. Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, PyMySQL (MySQL 8), Pydantic 2,
  Confluent Kafka client, psutil (for health metrics).
- **Dashboards:** plain HTML + CSS + vanilla JavaScript (`fetch`,
  `setInterval`) — no React/Vue/build step, no new frontend dependency.
  Served directly by FastAPI via `StaticFiles`/`FileResponse`.
- **DB:** MySQL 8 (`oms360_schema.sql` is the master schema).
- **Messaging:** Kafka (via `confluent-kafka`), topics defined in
  `app/config.py`.
- **Containerization:** Docker / docker-compose (`Dockerfile`,
  `docker-compose.yml`, both pre-existing, unchanged).

## 6. Folder Structure (this ZIP)

```
oms360_project/
├── CLAUDE_CONTEXT.md          <- this file
├── README.md                   (pre-existing, unchanged)
├── TEST_PLAN.md                (pre-existing, unchanged)
├── requirements.txt             (pre-existing, unchanged)
├── Dockerfile / docker-compose.yml  (pre-existing, unchanged)
├── oms360_schema.sql            (pre-existing master schema, unchanged)
├── migrations/                  (pre-existing, unchanged)
├── tests/                       (pre-existing, unchanged)
├── app/
│   ├── main.py                  <- MODIFIED (static mount + 2 HTML routes)
│   ├── config.py / database.py / models.py / schemas.py   (unchanged)
│   ├── core/                    (unchanged)
│   ├── messaging/                (unchanged)
│   ├── services/                 (unchanged)
│   ├── routes/
│   │   ├── dashboard.py         <- MODIFIED (6 new endpoints appended)
│   │   ├── health.py / orders.py / inventory.py / metrics.py  (unchanged)
│   └── static/                  <- NEW
│       ├── operations_dashboard.html   <- NEW (Dashboard 1)
│       └── monitoring_dashboard.html   <- NEW (Dashboard 2)
└── verification/                <- NEW, not part of the runtime app
    ├── mock_api.py               (throwaway mock server used only to
    │                              screenshot/verify the dashboards in an
    │                              offline sandbox with no MySQL/network)
    └── screenshots/              (Playwright screenshots taken against
                                    the mock server — desktop + tablet,
                                    both dashboards)
```

## 7. APIs Added

All new endpoints live in `app/routes/dashboard.py`, under the existing
`/api/v1/dashboard` prefix. `/operations` and `/analytics` already existed
and are unchanged.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/dashboard/kpis` | Bottom KPI bar: total orders/customers/sales/revenue, AOV, per-status counts |
| GET | `/api/v1/dashboard/live-orders?limit=` | Live Orders table feed |
| GET | `/api/v1/dashboard/kitchen-ops?limit=` | Kitchen Operations feed (chef, items, preparing/ready, time taken) |
| GET | `/api/v1/dashboard/delivery-ops?limit=` | Delivery Operations feed (partner, OTP state, route progress) |
| GET | `/api/v1/dashboard/alerts?limit=` | Merged business alerts (inventory + failed + duplicate orders) |
| GET | `/api/v1/dashboard/monitoring` | One aggregate snapshot for the entire Monitoring Center page |

Two new page routes in `app/main.py` (HTML, `include_in_schema=False`,
not part of the JSON API surface):

| Method | Path | Purpose |
|---|---|---|
| GET | `/dashboard/operations` | Serves Dashboard 1 HTML |
| GET | `/dashboard/monitoring` | Serves Dashboard 2 HTML |
| GET | `/dashboard` | Redirects to `/dashboard/operations` |
| — | `/dashboard/assets/*` | Static mount (`StaticFiles`) for the `app/static` folder |

## 8. Database Changes

**None.** No new tables, no new columns, no migration added. Every new
endpoint reads existing tables only: `orders_master`, `order_items`,
`kitchen_status`, `delivery_status`, `inventory`, `inventory_alerts`,
`failed_orders`, `duplicate_orders`, `dlq_orders`.

Two fields are explicitly-labeled **simulations**, because the schema has
no columns for them (documented in `app/routes/dashboard.py`'s module
docstring and inline comments too):

- **Delivery OTP code** — `delivery_status` has no OTP column. The 4-digit
  code shown is deterministically derived from the real `order_id`
  (SHA-256 hash → mod 10000), not random, not stored. `otp_generated` /
  `otp_verified` themselves are real booleans computed from the real
  `status` column (`OUT_FOR_DELIVERY`/`DELIVERED`).
- **Live GPS position** — `delivery_status` has no lat/lng or timestamp
  columns. The dashboard animates a rider icon along a fixed illustrative
  route client-side, driven by the real delivery status. This is the
  "Live GPS Simulation" the requirements explicitly asked for — not a
  claim of real telemetry.

## 9. Important Design Decisions

- **No architecture changes.** Did not touch the layered service
  structure, did not add new tables/columns, did not change any existing
  endpoint's contract or response shape. Followed the existing code style
  exactly (same docstring conventions, same "call service, don't touch
  ORM in routes" pattern was kept for new endpoints too, where practical
  — the new dashboard endpoints do direct read-only queries in the route,
  matching how `/operations` and `/analytics` already did it, rather than
  inventing a new service layer for read-only aggregation views).
- **No Jinja2 / template engine added.** The two dashboards are static
  HTML files with inline CSS/JS, served via `FileResponse` +
  `StaticFiles`. Zero new pip dependencies.
- **No new frontend framework.** Plain `fetch()` + `setInterval()`
  polling every 6 seconds. Chosen for reliability and zero build
  tooling, matching the "no redesign" instruction and keeping the
  deliverable a single HTML file per dashboard.
- **Environment constraint (important for continuity):** The sandbox
  this session ran in has **no network access** — `pip install` and
  `apt install` both fail, and no MySQL server is available. This means
  the real FastAPI app could not actually be booted against a real
  database in this session. What WAS verified:
  - Every modified/added `.py` file compiles (`python3 -m py_compile`).
  - Both dashboards' embedded JS passes `node --check`.
  - Both dashboards were rendered and screenshotted with Playwright
    (available offline in this sandbox) against a throwaway mock JSON
    server (`verification/mock_api.py`) whose responses are shaped
    exactly like the real `/api/v1/dashboard/*` endpoints. This
    confirmed layout, dark theme, alignment, spacing, and no-overlap at
    both desktop and tablet widths.
  - What was **not** verified: an actual MySQL connection, actual Kafka
    connectivity, and the app's behavior under `uvicorn` with a real ASGI
    server. This must be done in an environment with network access /
    the real `oms360_db` MySQL instance before calling this "production
    verified." See Section 4, item 1, for exact steps.
- **KPI bar is `position:fixed` to the viewport bottom** on Dashboard 1.
  If you re-screenshot with Playwright's `full_page=True`, the fixed bar
  will appear to "float" mid-page in the captured image — that's a known
  quirk of how headless Chromium stitches full-page screenshots with
  `position:fixed` elements, not a real bug. Confirmed correct behavior
  by taking a normal (non-full-page) screenshot after scrolling.
- **Deterministic OTP** rather than random: chosen so the same order
  always shows the same code across refreshes/screenshots, and so it's
  reviewable/reproducible rather than throwaway random noise.

## 10. Files Modified

- `app/main.py` — added `StaticFiles` mount + 2 dashboard HTML routes +
  `/dashboard` redirect. Existing routers/middleware/exception handlers
  untouched.
- `app/routes/dashboard.py` — appended 6 new endpoints (see Section 7)
  after the existing `/operations` and `/analytics` handlers, which are
  byte-for-byte unchanged. Also expanded the module docstring to explain
  the additions and the two simulated fields.

## 11. Files Added

- `app/static/operations_dashboard.html`
- `app/static/monitoring_dashboard.html`
- `CLAUDE_CONTEXT.md` (this file)
- `verification/mock_api.py` (offline test harness, not part of the
  runtime app — safe to delete before a production deploy, kept here so
  a future session can re-verify dashboard UI changes without needing a
  live DB)
- `verification/screenshots/*.png` (proof-of-verification screenshots
  from this session, taken against mock data, not the real DB)

## 12. Dashboard Requirements (for reference — what was asked for)

**Dashboard 1 — OMS-360 Enterprise Operations Center**
- Live Orders: Order ID, Customer ID, Customer Name, Ordered Items,
  Quantity, Total Amount, Payment Status, Order Time, Current Status ✅
- Kitchen Operations: Chef, Customer, Items, Preparing, Ready, Time
  Taken ✅
- Delivery Operations: Delivery Partner, Customer, Order, OTP Generated,
  OTP Verified, Live GPS Simulation, Delivery Status ✅
- Business Alerts ✅
- Order Lifecycle diagram (Order → Payment → Inventory → Kitchen →
  Ready → Delivery → Delivered) ✅
- Bottom KPI Bar: Total Orders, Total Customers, Total Sales, Total
  Revenue, Average Order Value, Pending, Preparing, Ready, Out for
  Delivery, Delivered, Cancelled ✅

**Dashboard 2 — OMS-360 Enterprise Monitoring Center**
- Application Health, Database, Kafka, Inventory, API Health, Docker,
  DLQ, Duplicate Orders, Failed Orders, Retry Queue ✅
- Inventory Summary, Kafka Summary, API Summary ✅
- Performance charts (CPU/memory/disk gauges, API latency bars) ✅
- Recent Alerts ✅

**Cross-cutting requirements**
- Professional dark theme ✅
- Modern enterprise UI ✅
- Simple English ✅
- Proper alignment / equal spacing / no overlapping ✅ (verified via
  screenshots, see Section 3/9)
- Responsive ✅ (verified at 1600px and 900px widths)
- Large tables ✅
- Professional KPI cards ✅
- Auto refresh (6s polling) ✅
- Live data only, no static business data ✅ (two clearly-documented
  UI-only simulations for OTP code + GPS animation, see Section 8)

## 14. Session 2 — Findings, Fixes, and What's Still Unverified

**Environment constraint still applies.** This sandbox also has no network
access — `pip install fastapi/sqlalchemy/pymysql/confluent-kafka` fails,
and no MySQL/Kafka can be started here. Nothing in this session was
actually run against a live stack. Everything below was verified by
reading the code and by `python3 -m py_compile` / `node --check` on every
changed file — same verification ceiling as Session 1 (see Section 9).
**You still need to run Section 4/13's steps (or RUN_GUIDE.md, added this
session) locally to get real end-to-end verification.**

### Root cause of the "invalid state combination" reports

You reported orders like `ORD-1000ABCD` (payment `FAILED`, order status
`RECEIVED`) and `ORD-1003ABCD` (payment `FAILED`, order status `READY`).
Tracing the code:

- `payment_service.mark_payment_failed()` — the only function in the
  entire codebase that ever sets `payment_status='FAILED'` — is **never
  called from anywhere** (`app/messaging/consumer.py`'s orchestrator has
  no failure branch, and no route calls it either). So the running app,
  as shipped, cannot itself produce a `FAILED` payment_status through a
  real order.
- Separately, `order_status` was **only ever written twice**: at creation
  (`RECEIVED`) and at final delivery (`DELIVERED`). Nothing updated it to
  `PREPARING`, `READY`, or `OUT_FOR_DELIVERY`, even though
  `kitchen_status`/`delivery_status` did track those stages correctly.
  So `current_status` on the dashboard could only ever legitimately show
  `RECEIVED` or `DELIVERED` before this session.

**Conclusion:** the specific rows you saw were not produced by running
`create_order` → the consumer → completion — that flow can't reach those
states. They're most likely from manual/direct SQL test rows inserted
into MySQL while poking at the dashboards (which makes sense — there was
no `demo_seed.sql` yet before this session, so hand-inserted test rows
were the only way to see non-empty tables). This isn't a criticism, just
the explanation, so you're not chasing a phantom bug in the running app
tonight. If you *do* see an invalid combo again after re-seeding with
`demo_seed.sql` and running a real order end-to-end (Step 9 in
RUN_GUIDE.md), that would be a genuine new bug worth reporting back with
the exact `order_id`.

### Fixes made this session

1. **`app/messaging/consumer.py`** — `_advance_order()` now writes
   `order_status` at every stage the orchestrator already visits
   (`PREPARING` when kitchen starts, `READY` when kitchen finishes,
   `OUT_FOR_DELIVERY` when dispatched, `DELIVERED` at the end —
   unchanged). Added a small `_set_order_status()` helper. No new
   columns/tables — this only writes the existing `order_status` column
   at points the code was already at.
2. **`app/messaging/consumer.py`** — moved
   `payment_service.mark_payment_successful()` to run **before** kitchen
   starts cooking (it previously ran after kitchen finished, meaning
   `payment_status` stayed `PENDING` for the entire `PREPARING` window).
   This matches the required valid workflow: `PAID` must precede
   `RECEIVED → PREPARING → ...`.
3. **`app/routes/dashboard.py`** — added `_check_state_validity()` and
   `_VALID_ORDER_STATUS_BY_PAYMENT`, a small table of which
   `order_status` values are legitimate for each `payment_status`
   (mirrors exactly the workflow you specified: `PENDING→RECEIVED` only;
   `PAID→RECEIVED/PREPARING/READY/OUT_FOR_DELIVERY/DELIVERED`;
   `FAILED→FAILED/CANCELLED`; `REFUNDED→DELIVERED/CANCELLED`). Applied to
   the `/live-orders` endpoint: every row now also returns `state_valid`
   (bool) and `state_issue` (string or null).
   **Deliberately does not hide/drop invalid rows** — an ops dashboard
   that silently filters out bad data can bury a real production bug.
   Instead each row is annotated so it's clearly flagged rather than
   presented as normal.
4. **`app/static/operations_dashboard.html`** — Live Orders table now
   shows a small red ⚠ next to `current_status` when `state_valid` is
   `false` (title/tooltip shows the reason), and lightly highlights the
   row. Pure CSS/markup addition, no layout change, `node --check` passes.
5. **`demo_seed.sql` / `demo_reset.sql`** (new, project root) — reset
   truncates all transactional tables + inventory/items; seed inserts 6
   orders covering every lifecycle stage (received/pending-payment,
   preparing, out-for-delivery, delivered, failed-payment, cancelled),
   one low-stock item, one out-of-stock item, one duplicate-order marker,
   one DLQ entry, one inventory alert. Every payment/order status pair in
   the seed data is intentionally valid per item 3 above.
6. **`RUN_GUIDE.md`** (new, project root) — start Docker/MySQL/Kafka,
   apply all 3 migrations (flags that `docker-compose.yml` only
   auto-applies schema + migration 002, not 003), start the API +
   consumer, open both dashboard URLs, load demo data, create a real test
   order and watch it progress, and a troubleshooting table.

### What was verified this session
- `python3 -m py_compile` on every modified/added `.py` file — all pass.
- `node --check` on both dashboards' embedded `<script>` blocks — both
  pass.
- Read-through of every service file that touches `order_status` /
  `payment_status` (`order_service.py`, `payment_service.py`,
  `kitchen_service.py`, `delivery_service.py`,
  `messaging/consumer.py`) to confirm the root-cause analysis above.

### What is still NOT verified (needs the real stack — see RUN_GUIDE.md)
- That the reordered payment-before-cooking sequence and the new
  `_set_order_status()` calls actually behave correctly against a real
  MySQL session (SQLAlchemy session/commit semantics, lock contention if
  the consumer and API touch the same row concurrently, etc.).
- That `/live-orders`' new `state_valid`/`state_issue` fields don't break
  anything for a client that wasn't expecting new JSON keys (dashboard
  JS was updated to use them; no other known consumer of this endpoint).
- Everything already flagged unverified in Section 4/9 from Session 1
  (real DB/Kafka connectivity, load under real traffic, auth).


1. [ ] Get this running in an environment with network + MySQL access.
2. [ ] Apply schema + migrations, start MySQL, start Kafka (or run with
       `OMS360_KAFKA_ENABLED=false` if Kafka isn't available yet).
3. [ ] `uvicorn app.main:app --reload` and hit both dashboard URLs.
4. [ ] Create a few test orders via `POST /api/v1/orders` and confirm
       they appear live on Dashboard 1 within one 6-second refresh cycle.
5. [ ] Confirm Dashboard 2's health tiles reflect real DB/Kafka state
       (try stopping Kafka/MySQL locally and confirm the dashboard shows
       DOWN/DEGRADED correctly).
6. [ ] Take final screenshots against the real stack for documentation.
7. [ ] Only after all of the above passes, consider this "final version"
       verified end-to-end as the user requested.
