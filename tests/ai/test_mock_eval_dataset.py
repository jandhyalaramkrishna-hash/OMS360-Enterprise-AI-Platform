"""
Tests for ai/evals/mock_dataset.py — MockEvalDataset.
"""

from ai.evals.base import EvalCase
from ai.evals.mock_dataset import MockEvalDataset


def test_cases_returns_non_empty_list_of_eval_cases():
    cases = MockEvalDataset().cases()
    assert len(cases) == 6
    assert all(isinstance(c, EvalCase) for c in cases)


def test_cases_have_unique_names():
    cases = MockEvalDataset().cases()
    names = [c.name for c in cases]
    assert len(names) == len(set(names))


def test_cases_each_have_a_callable_compare():
    for case in MockEvalDataset().cases():
        assert callable(case.compare)
        assert case.compare(f"[mock] {case.input}", case.expected) is True


def test_cases_returns_fresh_list_per_call():
    dataset = MockEvalDataset()
    first = dataset.cases()
    second = dataset.cases()
    assert first is not second
