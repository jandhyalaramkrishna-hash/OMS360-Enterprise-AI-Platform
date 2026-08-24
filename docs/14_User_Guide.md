# 14 — User Guide — OMS-360

**Consolidated:** 2026-08-04 (renumbered from `docs/User_Guide.md`,
content unchanged). This is the entry-point user guide — start here to
run the platform, place an order, and view the dashboards. For the full
command-by-command technical reference (manual steps, migration edge
cases, Windows launcher script internals, and a detailed troubleshooting
table), see `docs/15_Installation_Guide.md`, which this guide summarizes
rather than duplicates.

## 1. Prerequisites

- Docker + Docker Compose installed and running.
- Ports 3306 (MySQL), 9092 (Kafka), 2181 (Zookeeper), and 8000 (API) free.
- Windows users: Docker Desktop + PowerShell (present by default on
  Windows 10/11).

## 2. Start the Platform

**Windows (recommended):**

```bat
START_OMS360.bat
```

This starts MySQL/Zookeeper/Kafka (if not already running), builds and
starts the API and Kafka consumer, waits for a healthy `/health` response,
and opens Swagger and both dashboards in your browser automatically.

**Manual (any OS):**

```bash
docker compose up -d
cp .env.example .env   # first time only
```

See `docs/15_Installation_Guide.md` §0–5 for the full manual sequence,
including the one migration (`003_add_inventory_ledger.sql`) that needs a
one-time manual apply on a fresh database.

## 3. Confirm It's Running

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

Or, on Windows: `CHECK_OMS360.bat`. Or use the automated QA check:
`python postman/verify_stack_health.py` (never starts anything — verifies
only).

## 4. Explore the API

- **Swagger UI:** http://localhost:8000/docs — every endpoint documented,
  with "Try it out" against your running instance.
- **OpenAPI schema:** http://localhost:8000/openapi.json

## 5. Place Your First Order

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "customer_id": "CUST-TEST-01",
    "mobile": "9876543210",
    "payment_method": "ONLINE",
    "enterprise_id": "ENT-01",
    "delivery_address": {
      "door_no": "1", "street": "Test Street", "city": "Visakhapatnam",
      "state": "Andhra Pradesh", "pincode": "530001"
    },
    "items": [{"item_id": "ITEM-BURGER", "quantity": 1}]
  }'
```

Watch it move through `RECEIVED` → `PREPARING` → `READY` →
`OUT_FOR_DELIVERY` → `DELIVERED` on the Operations dashboard, updating
automatically every 6 seconds.

## 6. Explore the Dashboards

| Dashboard | URL | Shows |
|---|---|---|
| Operations Center | `/dashboard/operations` | Live order feed, KPIs, alerts |
| Monitoring Center | `/dashboard/monitoring` | System/Kafka/DB health tiles |
| Inventory | `/dashboard/inventory` | Stock levels, restock/add-item actions |
| AI Copilot | `/dashboard/ai-copilot` | Natural-language business Q&A over live data |

## 7. Load Demo Data (recommended before a demo)

```bash
docker exec -i oms360_mysql mysql -uroot -proot123 oms360_db < demo_reset.sql
docker exec -i oms360_mysql mysql -uroot -proot123 oms360_db < demo_seed.sql
```

Gives you one order in every lifecycle stage, a low-stock item, an
out-of-stock item, a duplicate-order marker, and a DLQ entry — every card
on every dashboard shows real data immediately.

## 8. Stop the Platform

```bat
STOP_OMS360.bat
```

Stops only the API and consumer — MySQL/Zookeeper/Kafka keep running so
you don't lose data between sessions.

## 9. Troubleshooting

The most common issues (empty dashboards, orders stuck at `RECEIVED`,
Kafka tile always down, `/health` reporting a DB error) and their fixes
are in `docs/15_Installation_Guide.md`'s troubleshooting table — check
there before filing a defect (`docs/11_Defect_Report.md`).

## 10. Running the QA Suite Yourself

If you want to verify the platform is behaving correctly rather than just
using it, see `docs/06_Test_Strategy.md` and `docs/16_QA_Automation_Guide.md`,
then run `Run_QA_Pipeline.bat` after starting the stack.
