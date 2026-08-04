"""
In-memory metrics. This is a QA/demo project, so a simple thread-safe
counter/rolling-average store is appropriate - no external metrics backend
required to see the numbers. Exposed via GET /metrics (app/routes/metrics.py)
as JSON. If you later want real Prometheus scraping, swap this module's
internals for `prometheus_client` without touching call sites - every
call site just does `metrics.increment(...)` / `metrics.record_api_call(...)`.
"""

import threading
from collections import defaultdict, deque

_lock = threading.Lock()

_counters = defaultdict(int)
_api_durations = defaultdict(lambda: deque(maxlen=500))   # path -> recent durations (ms)
_kafka_durations = deque(maxlen=500)                       # recent Kafka processing times (ms)


def increment(counter_name: str, amount: int = 1):
    with _lock:
        _counters[counter_name] += amount


def record_api_call(path: str, method: str, status_code: int, duration_ms: float):
    with _lock:
        _api_durations[f"{method} {path}"].append(duration_ms)
        _counters["api_requests_total"] += 1
        if status_code >= 500:
            _counters["api_requests_5xx"] += 1
        elif status_code >= 400:
            _counters["api_requests_4xx"] += 1


def record_kafka_processing_time(duration_ms: float):
    with _lock:
        _kafka_durations.append(duration_ms)
        _counters["kafka_messages_processed"] += 1


def _avg(values):
    values = list(values)
    return round(sum(values) / len(values), 2) if values else 0.0


def snapshot() -> dict:
    with _lock:
        api_summary = {
            path: {
                "count": len(durations),
                "avg_ms": _avg(durations),
                "max_ms": round(max(durations), 2) if durations else 0.0,
            }
            for path, durations in _api_durations.items()
        }
        return {
            "counters": dict(_counters),
            "api_response_times": api_summary,
            "kafka_processing_time_ms": {
                "count": len(_kafka_durations),
                "avg_ms": _avg(_kafka_durations),
                "max_ms": round(max(_kafka_durations), 2) if _kafka_durations else 0.0,
            },
        }
