"""
Tests for ai/evals/latency.py — LatencyAnalyzer.
"""

from ai.evals.base import EvalReport, EvalResult
from ai.evals.latency import LatencyAnalyzer, LatencyMetrics


def _report(timings):
    report = EvalReport()
    for i, t in enumerate(timings):
        report.results.append(
            EvalResult(case_name=f"case_{i}", passed=True, actual=None, expected=None, execution_time_ms=t)
        )
    return report


def test_analyze_computes_min_max_avg_total():
    analyzer = LatencyAnalyzer()
    metrics = analyzer.analyze(_report([10.0, 20.0, 30.0]))
    assert isinstance(metrics, LatencyMetrics)
    assert metrics.min_ms == 10.0
    assert metrics.max_ms == 30.0
    assert metrics.avg_ms == 20.0
    assert metrics.total_ms == 60.0
    assert metrics.sample_count == 3


def test_analyze_empty_report_returns_zeroed_metrics():
    analyzer = LatencyAnalyzer()
    metrics = analyzer.analyze(_report([]))
    assert metrics.min_ms == 0.0
    assert metrics.max_ms == 0.0
    assert metrics.avg_ms == 0.0
    assert metrics.total_ms == 0.0
    assert metrics.sample_count == 0


def test_analyze_ignores_results_with_no_recorded_timing():
    report = EvalReport()
    report.results.append(EvalResult(case_name="a", passed=True, actual=None, expected=None, execution_time_ms=None))
    report.results.append(EvalResult(case_name="b", passed=True, actual=None, expected=None, execution_time_ms=5.0))
    metrics = LatencyAnalyzer().analyze(report)
    assert metrics.sample_count == 1
    assert metrics.avg_ms == 5.0
