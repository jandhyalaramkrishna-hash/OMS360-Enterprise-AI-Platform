"""
AI Service Layer - Evals - Evaluation Reports (Sprint 8)
OMS-360 Enterprise Food Delivery Platform

EvaluationReportBuilder combines a raw EvalReport (Sprint 1) with
AccuracyScorer and LatencyAnalyzer (both Sprint 8) into one consolidated,
structured EvaluationSummary - the shape a future dashboard or API
response would actually want to return, rather than the raw
pass/fail list alone.
"""

from dataclasses import dataclass

from ai.evals.accuracy import AccuracyScore, AccuracyScorer
from ai.evals.base import EvalReport
from ai.evals.latency import LatencyMetrics, LatencyAnalyzer


@dataclass(frozen=True)
class EvaluationSummary:
    accuracy: AccuracyScore
    latency: LatencyMetrics
    case_results: list  # list[EvalResult], for detail drill-down


class EvaluationReportBuilder:
    def __init__(self, accuracy_scorer: AccuracyScorer = None, latency_analyzer: LatencyAnalyzer = None):
        self._accuracy_scorer = accuracy_scorer or AccuracyScorer()
        self._latency_analyzer = latency_analyzer or LatencyAnalyzer()

    def build(self, report: EvalReport) -> EvaluationSummary:
        return EvaluationSummary(
            accuracy=self._accuracy_scorer.score(report),
            latency=self._latency_analyzer.analyze(report),
            case_results=list(report.results),
        )
