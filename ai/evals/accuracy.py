"""
AI Service Layer - Evals - Accuracy Scoring (Sprint 8)
OMS-360 Enterprise Food Delivery Platform

AccuracyScorer turns a completed EvalReport into an AccuracyScore.
Deliberately kept separate from EvalReport.pass_rate (Sprint 1):
pass_rate is a raw property of the report itself, while AccuracyScorer is
the place a future, more nuanced accuracy definition (e.g. weighted
cases, partial credit) would live without changing EvalReport's shape.
"""

from dataclasses import dataclass

from ai.evals.base import EvalReport


@dataclass(frozen=True)
class AccuracyScore:
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy: float


class AccuracyScorer:
    def score(self, report: EvalReport) -> AccuracyScore:
        return AccuracyScore(
            total_cases=report.total,
            passed_cases=report.passed_count,
            failed_cases=report.total - report.passed_count,
            accuracy=report.pass_rate,
        )
