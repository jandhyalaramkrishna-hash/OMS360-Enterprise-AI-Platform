"""
AI Service Layer - Evals - Latency Metrics (Sprint 8)
OMS-360 Enterprise Food Delivery Platform

LatencyAnalyzer aggregates the per-case execution_time_ms values Sprint
8's EvalRunner change now stores on every EvalResult into min/max/avg/
total statistics for a completed EvalReport.
"""

from dataclasses import dataclass

from ai.evals.base import EvalReport


@dataclass(frozen=True)
class LatencyMetrics:
    min_ms: float
    max_ms: float
    avg_ms: float
    total_ms: float
    sample_count: int


class LatencyAnalyzer:
    def analyze(self, report: EvalReport) -> LatencyMetrics:
        timings = [r.execution_time_ms for r in report.results if r.execution_time_ms is not None]
        if not timings:
            return LatencyMetrics(min_ms=0.0, max_ms=0.0, avg_ms=0.0, total_ms=0.0, sample_count=0)
        return LatencyMetrics(
            min_ms=min(timings),
            max_ms=max(timings),
            avg_ms=round(sum(timings) / len(timings), 2),
            total_ms=round(sum(timings), 2),
            sample_count=len(timings),
        )
