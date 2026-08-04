"""
Tests for ai/evals/prompt_evaluator.py — PromptEvaluator running cases
through a provider's complete(), using the real MockAIProvider (Sprint
4) so this exercises an actual, if fully mock, end-to-end call.
"""

import asyncio

from ai.evals.base import EvalCase
from ai.evals.mock_dataset import MockEvalDataset
from ai.evals.prompt_evaluator import PromptEvaluator
from ai.evals.response_evaluator import exact_match
from ai.providers.mock_provider import MockAIProvider


def test_evaluate_with_mock_dataset_all_pass():
    evaluator = PromptEvaluator(MockAIProvider())
    report = asyncio.run(evaluator.evaluate(MockEvalDataset().cases()))
    assert report.total == 6
    assert report.passed_count == 6
    assert report.pass_rate == 1.0


def test_evaluate_records_execution_time_on_each_result():
    evaluator = PromptEvaluator(MockAIProvider())
    report = asyncio.run(evaluator.evaluate(MockEvalDataset().cases()))
    assert all(r.execution_time_ms is not None for r in report.results)


def test_evaluate_case_that_will_never_match_is_recorded_as_failed_not_crashed():
    cases = [EvalCase(name="never_matches", input="hello", expected="this-will-never-appear", compare=exact_match)]
    evaluator = PromptEvaluator(MockAIProvider())
    report = asyncio.run(evaluator.evaluate(cases))
    assert report.total == 1
    assert report.passed_count == 0
    assert report.results[0].error is None  # a false comparison is not a crash


def test_evaluate_with_a_failing_provider_is_recorded_as_error_not_crash():
    cases = [EvalCase(name="c1", input="hi", expected="hi", compare=exact_match)]
    evaluator = PromptEvaluator(MockAIProvider(simulate_failure=True))
    report = asyncio.run(evaluator.evaluate(cases))
    assert report.total == 1
    assert report.passed_count == 0
    assert report.results[0].error is not None
