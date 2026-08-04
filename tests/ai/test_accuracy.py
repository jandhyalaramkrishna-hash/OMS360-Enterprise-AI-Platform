"""
Tests for ai/evals/accuracy.py — AccuracyScorer.
"""

from ai.evals.accuracy import AccuracyScore, AccuracyScorer
from ai.evals.base import EvalReport, EvalResult


def _report(passed_flags):
    report = EvalReport()
    for i, passed in enumerate(passed_flags):
        report.results.append(EvalResult(case_name=f"case_{i}", passed=passed, actual=None, expected=None))
    return report


def test_score_all_passed():
    scorer = AccuracyScorer()
    score = scorer.score(_report([True, True, True]))
    assert isinstance(score, AccuracyScore)
    assert score.total_cases == 3
    assert score.passed_cases == 3
    assert score.failed_cases == 0
    assert score.accuracy == 1.0


def test_score_mixed():
    scorer = AccuracyScorer()
    score = scorer.score(_report([True, False, True, False]))
    assert score.total_cases == 4
    assert score.passed_cases == 2
    assert score.failed_cases == 2
    assert score.accuracy == 0.5


def test_score_empty_report_is_zero_not_error():
    scorer = AccuracyScorer()
    score = scorer.score(_report([]))
    assert score.total_cases == 0
    assert score.accuracy == 0.0
