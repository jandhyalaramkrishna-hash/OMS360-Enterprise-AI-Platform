# RUN_GUIDE.md — OMS-360

Step-by-step guide to running OMS-360 locally against a real MySQL + Kafka
stack, and opening both dashboards. Written for the Docker Compose setup
already in this repo (`docker-compose.yml`).

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
and `curl`. The four `.bat` files at the project root automate that same
workflow end-to-end, plus health polling, network auto-detection, and
timestamped logging. They start **only** the application layer
(`oms360-engine` + `oms360-consumer`) via `docker-compose.app.yml`, and
never redefine or restart MySQL/Zookeeper/Kafka if they're already up.

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
2. Check `oms360_mysql` / `oms360_zookeeper` / `oms360_kafka`. If any is
   not currently running, it starts that specific service via the
   existing `docker-compose.yml` (`docker compose up -d <service>`) —
   this does not duplicate or recreate an already-running container, it
   only brings up what's missing.
3. Wait for MySQL to report `healthy` (Docker healthcheck, up to 60s).
4. Detect the Docker network `oms360_mysql` is attached to and write it
   to `.env.oms360-app` (auto-generated — don't hand-edit).
5. Run `docker compose -f docker-compose.app.yml --env-file
   .env.oms360-app up -d --build` — starts/rebuilds **only**
   `oms360-engine` and `oms360-consumer`.
6. Poll `GET http://localhost:8000/health` until it returns HTTP 200
   (up to 90s), and reports the JSON `status` field
   (HEALTHY/WARNING/DEGRADED) — a 200 alone doesn't mean fully healthy;
   check the printed status.
7. Open Swagger and both dashboards in your default browser.
8. Print a startup summary banner.

Every run appends timestamped entries to `logs\startup.log`.

> **First run only:** this script does not apply
> `migrations/003_add_inventory_ledger.sql` or load demo data — that's
> still Steps 1 and 8 above (`docker exec -i oms360_mysql mysql ...`).
> The launcher only orchestrates container startup, not schema/data setup.

### 2. Check status any time

```bat
CHECK_OMS360.bat
```

Prints Docker status, MySQL/Zookeeper/Kafka container state + Docker
healthcheck status (where one is defined — Zookeeper/Kafka/Consumer don't
define a Docker healthcheck in this project, so only their running state
is shown), Engine/Consumer container state, HTTP status for `/health`,
`/docs`, `/dashboard/operations`, `/dashboard/monitoring`, the detected
Docker network, and TCP port status for 3306/2181/9092/8000. Appends to
`logs\health.log`.

### 3. Restart just the app layer

```bat
RESTART_OMS360.bat
```

Runs `STOP_OMS360.bat` then `START_OMS360.bat`. Infra is never touched.

### 4. Stop the app layer

```bat
STOP_OMS360.bat
```

Stops only `oms360_core_engine` and `oms360_consumer`. MySQL, Zookeeper,
and Kafka keep running so you don't lose data/state between sessions.

### Troubleshooting the launcher scripts specifically

| Symptom | Likely cause |
|---|---|
| `START_OMS360.bat` fails at "Detecting Docker network" | `oms360_mysql` isn't running yet, or was renamed. Run `docker ps` to confirm the container name and that it's up. |
| `.env.oms360-app` has an unexpected/stale network name | Delete it and re-run `START_OMS360.bat` — it's regenerated on every run, safe to delete anytime. |
| Engine health check times out at 90s but `docker ps` shows it running | Check `docker logs oms360_core_engine` — commonly a DB auth error if MySQL's root password was changed from the `docker-compose.yml` default (`root123`) without updating `docker-compose.app.yml` to match. |
| `CHECK_OMS360.bat` shows Kafka/Zookeeper with `health=NONE` | Expected — this project's `docker-compose.yml` does not define a Docker healthcheck for those two services, only for MySQL and the Engine. `NONE` means "no healthcheck defined," not "unhealthy." Running state is still shown. |
| Scripts appear to hang on a PowerShell call | Corporate/locked-down PowerShell execution policy can block `-Command` calls. Confirm with `powershell -NoProfile -Command "Get-Date"` directly in a terminal. |
