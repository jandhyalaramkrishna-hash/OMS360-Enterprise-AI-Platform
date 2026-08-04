"""
Tests for ai/evals/reports.py — EvaluationReportBuilder.
"""

from ai.evals.base import EvalReport, EvalResult
from ai.evals.reports import EvaluationReportBuilder, EvaluationSummary


def test_build_combines_accuracy_latency_and_case_results():
    report = EvalReport()
    report.results.append(
        EvalResult(case_name="a", passed=True, actual="x", expected="x", execution_time_ms=10.0)
    )
    report.results.append(
        EvalResult(case_name="b", passed=False, actual="y", expected="z", execution_time_ms=20.0)
    )

    summary = EvaluationReportBuilder().build(report)

    assert isinstance(summary, EvaluationSummary)
    assert summary.accuracy.total_cases == 2
    assert summary.accuracy.passed_cases == 1
    assert summary.accuracy.accuracy == 0.5
    assert summary.latency.sample_count == 2
    assert summary.latency.avg_ms == 15.0
    assert len(summary.case_results) == 2
    assert summary.case_results[0].case_name == "a"


def test_build_with_empty_report():
    summary = EvaluationReportBuilder().build(EvalReport())
    assert summary.accuracy.total_cases == 0
    assert summary.latency.sample_count == 0
    assert summary.case_results == []
