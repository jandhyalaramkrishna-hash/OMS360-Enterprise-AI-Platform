"""
AI Service Layer - Metrics
OMS-360 Enterprise Food Delivery Platform

In-process counters for the AI Service Layer: request count, response
count, provider latency, token usage, error count. Sprint 2 scope: no
external monitoring integration (no Prometheus/Datadog export) - these
are real, thread-safe in-memory counters a future sprint can wire to
app.core.metrics or an external system, not fake/demo values. Placed at
the ai/ package root (rather than under ai/services/) to mirror the
existing app.core.metrics module's flat, easy-to-import shape.
"""

import threading
from dataclasses import dataclass, field

from app.core.logging_config import get_logger

logger = get_logger("ai.metrics")

_lock = threading.Lock()


@dataclass
class AIMetricsSnapshot:
    request_count: int = 0
    response_count: int = 0
    error_count: int = 0
    token_usage_total: int = 0
    provider_latency_ms: dict = field(default_factory=dict)  # provider_name -> list of ms samples


class AIMetrics:
    """Process-lifetime singleton. Access via get_ai_metrics()."""

    def __init__(self):
        self._request_count = 0
        self._response_count = 0
        self._error_count = 0
        self._token_usage_total = 0
        self._provider_latency_ms = {}

    def record_request(self) -> None:
        with _lock:
            self._request_count += 1

    def record_response(self, token_usage: int = 0) -> None:
        with _lock:
            self._response_count += 1
            self._token_usage_total += max(0, token_usage)

    def record_error(self) -> None:
        with _lock:
            self._error_count += 1

    def record_provider_latency(self, provider_name: str, latency_ms: float) -> None:
        with _lock:
            self._provider_latency_ms.setdefault(provider_name, []).append(round(latency_ms, 2))

    def snapshot(self) -> AIMetricsSnapshot:
        with _lock:
            return AIMetricsSnapshot(
                request_count=self._request_count,
                response_count=self._response_count,
                error_count=self._error_count,
                token_usage_total=self._token_usage_total,
                provider_latency_ms={k: list(v) for k, v in self._provider_latency_ms.items()},
            )

    def reset(self) -> None:
        """Test-only helper - resets all counters. Not used by production code paths."""
        with _lock:
            self._request_count = 0
            self._response_count = 0
            self._error_count = 0
            self._token_usage_total = 0
            self._provider_latency_ms = {}


_metrics = AIMetrics()


def get_ai_metrics() -> AIMetrics:
    return _metrics
