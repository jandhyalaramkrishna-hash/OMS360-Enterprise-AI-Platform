"""
Tests for ai/evals — EvalRunner against passing, failing, and
exception-raising cases.
"""

import asyncio

from ai.evals.base import EvalCase
from ai.evals.runner import EvalRunner


async def _double(x):
    return x * 2


async def _always_raises(x):
    raise RuntimeError("target failed")


def test_eval_runner_all_pass():
    cases = [
        EvalCase(name="doubles_2", input=2, expected=4, compare=lambda a, e: a == e),
        EvalCase(name="doubles_5", input=5, expected=10, compare=lambda a, e: a == e),
    ]
    report = asyncio.run(EvalRunner().run(cases, _double))
    assert report.total == 2
    assert report.passed_count == 2
    assert report.pass_rate == 1.0


def test_eval_runner_mixed_pass_fail():
    cases = [
        EvalCase(name="correct", input=2, expected=4, compare=lambda a, e: a == e),
        EvalCase(name="wrong_expectation", input=2, expected=999, compare=lambda a, e: a == e),
    ]
    report = asyncio.run(EvalRunner().run(cases, _double))
    assert report.total == 2
    assert report.passed_count == 1
    assert report.pass_rate == 0.5


def test_eval_runner_target_exception_recorded_as_failure_not_crash():
    cases = [EvalCase(name="raises", input=1, expected=1, compare=lambda a, e: a == e)]
    report = asyncio.run(EvalRunner().run(cases, _always_raises))
    assert report.total == 1
    assert report.passed_count == 0
    assert report.results[0].error == "target failed"


def test_eval_report_pass_rate_zero_cases_is_zero_not_error():
    report = asyncio.run(EvalRunner().run([], _double))
    assert report.total == 0
    assert report.pass_rate == 0.0
