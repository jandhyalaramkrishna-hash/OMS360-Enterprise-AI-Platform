# 15 — Installation Guide — OMS-360

**Consolidated:** 2026-08-04 (renumbered from `docs/RUN_GUIDE.md`, content
unchanged). Step-by-step guide to running OMS-360 locally against a real
MySQL + Kafka stack, and opening both dashboards. Written for the Docker
Compose setup already in this repo (`docker-compose.yml`). For the
reader-facing quick-start summary, see `docs/14_User_Guide.md`, which
this document underlies.

---

## 0. Prerequisites

- Docker + Docker Compose installed and running
- Python 3.10+ (only needed if you run the FastAPI app outside Docker)
- Port 3306 (MySQL), 9092 (Kafka), 2181 (Zookeeper), and 8000 (API) free

## 1. Start Docker, MySQL, and Kafka

From the project root:

```bash
docker compose up -d mysql zookeeper kafka
```

Wait for MySQL to report healthy (it applies `oms360_schema.sql` and
`migrations/002_add_audit_trail.sql` automatically on first boot, via the
`docker-entrypoint-initdb.d` mount):

```bash
docker compose ps
# oms360_mysql should show "healthy"
```

> **First run only:** `migrations/003_add_inventory_ledger.sql` is **not**
> auto-applied by docker-compose (only `oms360_schema.sql` and `002` are
> mounted into `docker-entrypoint-initdb.d`). Apply it manually once:
> ```bash
> docker exec -i oms360_mysql mysql -uroot -proot123 oms360_db < migrations/003_add_inventory_ledger.sql
> ```
> Skip this only if you're intentionally not using the inventory ledger
> feature.

## 2. Apply migrations (if not using Docker's auto-init)

If you're running MySQL yourself (not via the compose file above), apply
these in order against your `oms360_db` database:

```bash
mysql -u <user> -p oms360_db < oms360_schema.sql
mysql -u <user> -p oms360_db < migrations/002_add_audit_trail.sql
mysql -u <user> -p oms360_db < migrations/003_add_inventory_ledger.sql
```

## 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if your MySQL/Kafka aren't on the defaults. If running the
FastAPI app **outside** Docker (talking to the Dockerized MySQL/Kafka on
your host), keep `OMS360_DB_HOST=127.0.0.1` and
`KAFKA_BOOTSTRAP_SERVERS=localhost:9092`. If running the app itself
**inside** Docker via `docker compose up`, it already uses the in-network
hostnames (`mysql`, `kafka:29092`) — see `docker-compose.yml`.

## 4. Install dependencies (only if running outside Docker)

```bash
pip install -r requirements.txt
```

## 5. Start the FastAPI app

**Option A — everything via Docker Compose (recommended):**

```bash
docker compose up -d
```

This also starts `oms360-engine` (the API) and `oms360-consumer` (the
Kafka consumer that advances orders through kitchen → payment →
delivery — see `app/messaging/consumer.py`). Without the consumer
running, orders will sit at `RECEIVED` forever, since nothing else
advances them.

**Option B — API locally, infra in Docker:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

And in a second terminal, start the consumer (required — see note above):

```bash
python -m app.messaging.consumer
```

## 6. Confirm health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

Both should return 200 with no errors.

## 7. Open the dashboards

- Operations Center: http://localhost:8000/dashboard/operations
- Monitoring Center: http://localhost:8000/dashboard/monitoring
- (`http://localhost:8000/dashboard` redirects to Operations)

Both pages poll their JSON endpoints every 6 seconds automatically — no
manual refresh needed.

## 8. Load demo data (optional, recommended before a demo/interview)

```bash
docker exec -i oms360_mysql mysql -uroot -proot123 oms360_db < demo_reset.sql
docker exec -i oms360_mysql mysql -uroot -proot123 oms360_db < demo_seed.sql
```

(Swap the `docker exec` prefix for a plain `mysql -u <user> -p oms360_db <
...` if you're not using Docker for MySQL.) This gives you one order in
each stage of the lifecycle, a low-stock item, an out-of-stock item, a
duplicate-order marker, and a DLQ entry — enough for every card on both
dashboards to show real, non-empty data immediately.

## 9. Create a real order and watch it move

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

Watch it on Dashboard 1 — it should appear within one 6-second refresh at
`RECEIVED`, move to `PREPARING` once the consumer picks it up, then
`READY`, `OUT_FOR_DELIVERY`, and finally `DELIVERED` (timing controlled by
`OMS360_SIM_COOKING_SECONDS` / `OMS360_SIM_DELIVERY_SECONDS` in `.env`).

## 10. Verify DB/Kafka failure states on Dashboard 2

To confirm the Monitoring Center correctly shows `DOWN`/`DEGRADED`:

```bash
docker compose stop kafka
# refresh http://localhost:8000/dashboard/monitoring — Kafka tile should
# go DOWN within one refresh cycle
docker compose start kafka
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Dashboards load but all tables are empty | No orders yet — run demo_seed.sql or create a test order (Step 9) |
| Orders stuck at `RECEIVED` forever | The consumer (`app.messaging.consumer`) isn't running — see Step 5 |
| `/health` returns DB error | MySQL not up yet, or `.env` credentials wrong |
| Kafka tile always shows DOWN | `kafka` container not healthy yet — Kafka takes longer to boot than MySQL; wait and retry |
| A row shows a red ⚠ next to its status on Dashboard 1 | The dashboard's business-rule validation flagged an invalid `payment_status`/`order_status` combination on that row (see `app/routes/dashboard.py`'s `_check_state_validity`) — hover the icon for the reason, then check how that row got that combination (manual DB edit vs. a real code path) |

---

## Windows Launcher Scripts (alternative to manual steps above)

Everything in Steps 0–10 above can be done manually with `docker compose`
and `curl`. The four `.bat` files at the project root/`scripts\` automate
that same workflow end-to-end against the **single, unified
`docker-compose.yml`** (the separate `docker-compose.app.yml` file some
older notes reference is legacy/optional and is not used by any of these
four scripts), plus health polling, per-container verification, and
timestamped logging.

**Update, 2026-08-04:** this section was corrected to match the scripts'
actual current behavior (it previously described an older, since-replaced
design that used a separate `docker-compose.app.yml`, an auto-generated
`.env.oms360-app` file, and per-service `docker compose up -d <service>`
calls — none of that exists in the current scripts). It was also updated
for the same day's `STOP_OMS360.bat` change described below.

### Prerequisites (same as Steps 0–1 above, plus)

- Windows with Docker Desktop, and PowerShell available (used internally
  for timestamps, health polling, and port checks — present by default on
  Windows 10/11).
- Run these from the project root (same folder as `docker-compose.yml`).

### 1. Start everything

```bat
START_OMS360.bat
```

This will, in order:
1. Verify Docker Desktop is running.
2. Clean up any previous OMS360 environment (`docker compose down
   --remove-orphans` plus a belt-and-suspenders removal of this project's
   own fixed-name containers/network only — never anything from another
   Docker project).
3. Check and free ports 3306/2181/9092/8000 if a stale process is still
   holding one of them.
4. Run `docker compose -f docker-compose.yml up -d --build --wait
   --wait-timeout 300` — brings up **all five services** (mysql,
   zookeeper, kafka, oms360-engine, oms360-consumer) in one call, and
   waits for Docker's own healthchecks to confirm each is actually ready
   (not just running) before continuing. This is idempotent: anything
   already running and unchanged is left alone; only what's missing,
   stopped, or out of date is (re)created.
5. Independently re-verify each container's state (belt-and-suspenders on
   top of step 4's `--wait`).
6. Confirm the Engine's `GET /health` endpoint directly and report its
   JSON `status` field (HEALTHY/WARNING/DEGRADED) — HTTP 200 alone doesn't
   mean fully healthy; check the printed status.
7. Open Swagger and the Inventory dashboard in Microsoft Edge.

Every run appends timestamped entries to `logs\startup.log`.

> **First run only:** this script does not apply
> `migrations/003_add_inventory_ledger.sql` — that's still Step 2 above
> (`docker exec -i oms360_mysql mysql ...`). Demo data (menu/inventory
> items) and the `002`/`004` migrations, unlike `003`, **are** applied
> automatically on a brand-new MySQL volume via `docker-compose.yml`'s
> own init-script mounts. The launcher orchestrates container startup and
> health verification; it does not run one-off manual migrations.

### 2. Check status any time

```bat
CHECK_OMS360.bat
```

Prints Docker Desktop status; MySQL/Zookeeper/Kafka container state +
Docker healthcheck status (all three now define a real healthcheck in
`docker-compose.yml`); Engine/Consumer container state + health (Consumer
has no Docker healthcheck defined — container state only); HTTP status
for `/health`, Swagger, the Operations dashboard, and the Monitoring
dashboard; the Docker network `oms360_mysql` is attached to (flags a
mismatch against the fixed `oms360_network` name as a likely sign of a
stale pre-fix container); and TCP port status for 3306/2181/9092/8000.
Appends to `logs\health.log`.

### 3. Restart the stack

```bat
RESTART_OMS360.bat
```

Runs `STOP_OMS360.bat` then `START_OMS360.bat`. **As of the 2026-08-04
`STOP_OMS360.bat` update below, this now restarts the complete stack**
(MySQL, Zookeeper, Kafka, Engine, Consumer) rather than the application
layer only, since the stop phase it calls now stops everything. All data
and volumes are preserved throughout — nothing is removed, only stopped
and brought back up. (`RESTART_OMS360.bat`'s own on-screen banner text
still describes the older app-layer-only behavior; this is a known,
disclosed follow-up — the script's actual behavior is what's documented
here.)

### 4. Stop everything

```bat
STOP_OMS360.bat
```

**Updated 2026-08-04:** stops the **complete** OMS360 stack — MySQL,
Zookeeper, Kafka, Engine, and Consumer — via `docker compose -f
docker-compose.yml stop` (falling back to per-container `docker stop`
calls, using this project's own fixed container names only, if the
compose call reports an error). This only ever touches containers
belonging to this project's own `docker-compose.yml`; it never runs a
global command like `docker stop $(docker ps ...)` that could affect an
unrelated Docker project on the same machine, and it never runs `docker
compose down -v` — no volumes, data, or images are ever removed. Run
`START_OMS360.bat` again at any time to bring the same stack back up with
all data intact. Ends with a shutdown summary banner confirming each
service's stopped state and that the database/volumes were preserved.

### Troubleshooting the launcher scripts specifically

| Symptom | Likely cause |
|---|---|
| Engine health check times out but `docker ps` shows it running | Check `docker logs oms360_core_engine` — commonly a DB auth error if MySQL's root password was changed from the `docker-compose.yml` default (`root123`) without updating the engine/consumer service's own environment block in the same file to match. |
| `CHECK_OMS360.bat` shows Kafka/Zookeeper/MySQL with `health=` anything other than `healthy`/`starting` | All three define a real Docker healthcheck in `docker-compose.yml` — `unhealthy` or a state stuck at `starting` past the normal boot window is a real problem, not just "no healthcheck defined." Check `docker logs <container>`. |
| `STOP_OMS360.bat` reports a container still running after "docker compose stop" | Rare — usually a container mid-restart or wedged. Re-run `STOP_OMS360.bat`, or run `docker compose -f docker-compose.yml stop <service>` directly for the specific service named in the warning. |
| Scripts appear to hang on a PowerShell call | Corporate/locked-down PowerShell execution policy can block `-Command`/`-File` calls. Confirm with `powershell -NoProfile -Command "Get-Date"` directly in a terminal. |
