"""
Tests for ai/evals/evaluation_service.py — EvaluationService:
capability-gated evaluate(), delegating to EvalRunner + EvaluationReportBuilder.
"""

import asyncio

import pytest

from ai.core.exceptions import AIFeatureDisabledError
from ai.evals.base import EvalCase
from ai.evals.evaluation_service import EvaluationService
from ai.evals.reports import EvaluationReportBuilder, EvaluationSummary
from ai.evals.runner import EvalRunner
from ai.providers.mock_provider import MockAIProvider
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.ai_service import AIService


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    if "evals_enabled" in overrides:
        base["feature_flags"] = {**base["feature_flags"], "evals_enabled": overrides["evals_enabled"]}
    return RuntimeConfiguration(**base)


def _ai_service(ai_enabled=True, evals_enabled=True):
    registry = ProviderRegistry()
    registry.register(MockAIProvider())
    return AIService(_runtime_config(ai_enabled=ai_enabled, evals_enabled=evals_enabled), ValidationResult(), registry)


def _make_service(ai_enabled=True, evals_enabled=True):
    return EvaluationService(EvalRunner(), EvaluationReportBuilder(), _ai_service(ai_enabled, evals_enabled))


async def _double(x):
    return x * 2


def test_evaluate_returns_evaluation_summary():
    service = _make_service()
    cases = [EvalCase(name="c1", input=2, expected=4, compare=lambda a, e: a == e)]
    summary = asyncio.run(service.evaluate(cases, _double))
    assert isinstance(summary, EvaluationSummary)
    assert summary.accuracy.total_cases == 1
    assert summary.accuracy.accuracy == 1.0


def test_evaluate_raises_when_ai_disabled():
    service = _make_service(ai_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.evaluate([], _double))


def test_evaluate_raises_when_evals_capability_disabled():
    service = _make_service(evals_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.evaluate([], _double))
