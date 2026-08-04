import shutil
import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.core.enums import HealthStatus
from app.core.kafka_admin import get_topic_stats
from app.database import get_db, get_pool_stats

router = APIRouter(tags=["Health"])


@router.get("/", summary="Root ping")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION, "status": "UP"}


@router.get("/version", summary="Application version")
def version():
    return {
        "version": settings.APP_VERSION,
        "build_version": settings.BUILD_VERSION,
        "environment": settings.APP_ENV,
    }


def _check_database(db: Session) -> dict:
    start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "UP", "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
                "pool": get_pool_stats()}
    except Exception as exc:
        return {"status": "DOWN", "error": str(exc)}


def _check_kafka_broker() -> dict:
    if not settings.KAFKA_ENABLED:
        return {"status": "DISABLED"}
    start = time.perf_counter()
    stats = get_topic_stats()
    stats["response_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
    stats["status"] = "UP" if stats.get("broker_reachable") else "DOWN"
    return stats


def _check_kafka_producer() -> str:
    """Non-critical: producer is lazily created on first publish - if
    nothing has published yet, this reports NOT_INITIALIZED rather than
    falsely claiming UP or DOWN."""
    from app.messaging import producer as producer_module
    if not settings.KAFKA_ENABLED:
        return "DISABLED"
    if producer_module._producer is None:
        return "NOT_INITIALIZED"
    return "DOWN" if producer_module._producer is False else "UP"


def _check_disk() -> dict:
    try:
        usage = shutil.disk_usage("/")
        percent_used = round((usage.used / usage.total) * 100, 1)
        return {"status": "OK" if percent_used < 90 else "WARNING", "percent_used": percent_used}
    except Exception as exc:
        return {"status": "UNKNOWN", "error": str(exc)}


def _check_memory() -> dict:
    try:
        import psutil
        percent_used = psutil.virtual_memory().percent
        return {"status": "OK" if percent_used < 90 else "WARNING", "percent_used": percent_used}
    except ImportError:
        return {"status": "UNKNOWN", "error": "psutil not installed"}
    except Exception as exc:
        return {"status": "UNKNOWN", "error": str(exc)}


def _check_cpu() -> dict:
    try:
        import psutil
        percent_used = psutil.cpu_percent(interval=0.1)
        return {"status": "OK" if percent_used < 90 else "WARNING", "percent_used": percent_used}
    except ImportError:
        return {"status": "UNKNOWN", "error": "psutil not installed"}
    except Exception as exc:
        return {"status": "UNKNOWN", "error": str(exc)}


def _check_docker() -> str:
    """Best-effort: true when running inside a container (matches
    settings.DOCKER_MODE, set via the DOCKER_MODE env var in
    docker-compose.yml). Doesn't shell out to the Docker daemon from
    inside the app container - that needs the docker socket mounted in, a
    security tradeoff out of scope here."""
    return "CONTAINERIZED" if settings.DOCKER_MODE else "NOT_CONTAINERIZED"


def _compute_overall_status(db_check: dict, kafka_check: dict, disk_check: dict,
                             memory_check: dict, cpu_check: dict) -> str:
    """Shared with app/routes/dashboard.py's monitoring_snapshot() (2026-07-25
    UX redesign) so the Monitoring Center's "Live Backend Status" reflects
    the exact same HEALTHY/WARNING/DEGRADED logic GET /health uses - not a
    second, potentially-drifting copy of this rule."""
    critical_ok = db_check["status"] == "UP"
    non_critical_warning = any(
        c.get("status") in ("WARNING", "DOWN", "UNKNOWN")
        for c in (kafka_check, disk_check, memory_check, cpu_check)
    )
    if not critical_ok:
        return HealthStatus.DEGRADED.value
    if non_critical_warning:
        return HealthStatus.WARNING.value
    return HealthStatus.HEALTHY.value


@router.get(
    "/health",
    response_model=schemas.SystemHealthResponse,
    summary="Aggregate health check",
    description=(
        "Reports MySQL, Kafka broker/topics/producer/consumer-config, disk, "
        "memory, CPU, Docker mode, DB connection pool stats, build/version "
        "info, and an overall status of HEALTHY/WARNING/DEGRADED/DOWN. "
        "Database is CRITICAL (its failure alone forces DEGRADED); "
        "Kafka/disk/memory/CPU are NON-CRITICAL (a problem there yields "
        "WARNING, not DEGRADED) - the API can still serve most read "
        "endpoints without Kafka."
    ),
)
def health(db: Session = Depends(get_db)):
    db_check = _check_database(db)
    kafka_check = _check_kafka_broker()
    disk_check = _check_disk()
    memory_check = _check_memory()
    cpu_check = _check_cpu()

    db_status_str = db_check["status"]
    if db_check.get("response_time_ms"):
        db_status_str += f" ({db_check['response_time_ms']}ms)"

    dependencies = {
        "application": "UP",
        "database": db_status_str,
        "kafka_broker": kafka_check.get("status", "UNKNOWN"),
        "kafka_producer": _check_kafka_producer(),
        "kafka_consumer_group": settings.KAFKA_CONSUMER_GROUP,
        "disk": f"{disk_check['status']} ({disk_check.get('percent_used', '?')}% used)",
        "memory": f"{memory_check['status']} ({memory_check.get('percent_used', '?')}% used)",
        "cpu": f"{cpu_check['status']} ({cpu_check.get('percent_used', '?')}% used)",
        "docker": _check_docker(),
        "redis": "NOT_CONFIGURED",
        "build_version": settings.BUILD_VERSION,
        "environment": settings.APP_ENV,
        "db_pool": str(db_check.get("pool", "-")),
    }

    overall = _compute_overall_status(db_check, kafka_check, disk_check, memory_check, cpu_check)

    return schemas.SystemHealthResponse(status=overall, dependencies=dependencies)
