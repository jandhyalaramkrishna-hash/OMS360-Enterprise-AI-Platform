"""
Tests for the Sprint 8 additions to ai/dependencies.py — the assembled
evaluation pipeline singletons, and that PromptEvaluator uses the SAME
shared "mock" provider Sprint 2/4 already registered, not a second one.
"""

from ai.dependencies import (
    get_accuracy_scorer,
    get_ai_service,
    get_eval_runner,
    get_evaluation_report_builder,
    get_evaluation_service,
    get_latency_analyzer,
    get_mock_eval_dataset,
    get_prompt_evaluator,
    get_provider_registry,
)
from ai.evals.accuracy import AccuracyScorer
from ai.evals.evaluation_service import EvaluationService
from ai.evals.latency import LatencyAnalyzer
from ai.evals.mock_dataset import MockEvalDataset
from ai.evals.prompt_evaluator import PromptEvaluator
from ai.evals.reports import EvaluationReportBuilder


def test_sprint8_providers_return_singletons():
    assert get_accuracy_scorer() is get_accuracy_scorer()
    assert get_latency_analyzer() is get_latency_analyzer()
    assert get_evaluation_report_builder() is get_evaluation_report_builder()
    assert get_mock_eval_dataset() is get_mock_eval_dataset()
    assert get_prompt_evaluator() is get_prompt_evaluator()
    assert get_evaluation_service() is get_evaluation_service()


def test_get_accuracy_scorer_returns_instance():
    assert isinstance(get_accuracy_scorer(), AccuracyScorer)


def test_get_latency_analyzer_returns_instance():
    assert isinstance(get_latency_analyzer(), LatencyAnalyzer)


def test_get_evaluation_report_builder_returns_instance():
    assert isinstance(get_evaluation_report_builder(), EvaluationReportBuilder)


def test_get_mock_eval_dataset_returns_instance():
    assert isinstance(get_mock_eval_dataset(), MockEvalDataset)


def test_get_prompt_evaluator_returns_instance():
    assert isinstance(get_prompt_evaluator(), PromptEvaluator)


def test_get_evaluation_service_returns_instance():
    assert isinstance(get_evaluation_service(), EvaluationService)


def test_prompt_evaluator_uses_the_shared_mock_provider():
    assert get_prompt_evaluator()._provider is get_provider_registry().get_provider("mock")


def test_evaluation_service_shares_the_same_eval_runner_singleton():
    assert get_evaluation_service()._runner is get_eval_runner()


def test_evaluation_service_shares_the_same_ai_service_singleton():
    assert get_evaluation_service()._ai_service is get_ai_service()
