from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import metrics
from app.core.kafka_admin import get_dlq_summary
from app.database import get_db

router = APIRouter(tags=["Metrics"])


@router.get(
    "/metrics",
    summary="In-memory + DB-backed application metrics",
    description=(
        "In-memory: orders processed/failed/cancelled, duplicate requests, "
        "Kafka publish/consume/retry/DLQ counts, API response times, Kafka "
        "processing time. DB-backed: total DLQ messages and the 5 most "
        "recent, from dlq_orders. In-memory counters reset on restart; "
        "swap app/core/metrics.py for prometheus_client later if you need "
        "persistence/scraping without changing any call site."
    ),
)
def get_metrics(db: Session = Depends(get_db)):
    snapshot = metrics.snapshot()
    snapshot["dlq"] = get_dlq_summary(db)
    return snapshot
