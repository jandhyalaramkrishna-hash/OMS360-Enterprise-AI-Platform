"""
Tests for ai/copilot/qa_assistant_service.py — QAAssistantService.generate()
in both the deterministic-template (no provider) and AI-generated (stub
provider) paths, plus test_types normalization.
"""

import asyncio

from ai.copilot.provider_manager import AIProviderManager, ProviderSelection
from ai.copilot.qa_assistant_service import QAAssistantService
from ai.providers.registry import ProviderRegistry


class _StubProvider:
    name = "stub"

    def __init__(self, text):
        self._text = text

    async def complete(self, prompt: str, **kwargs) -> dict:
        return {"content": self._text}


class _FailingProvider:
    name = "failing"

    async def complete(self, prompt, **kwargs):
        raise RuntimeError("simulated provider failure")


class _StubProviderManager:
    def __init__(self, provider=None):
        self._selection = ProviderSelection(provider=provider, source="auto", reasoning_available=provider is not None)

    def get_active_provider(self):
        return self._selection


def _no_provider_service():
    return QAAssistantService(AIProviderManager(ProviderRegistry()))


def test_generate_no_provider_uses_deterministic_template():
    service = _no_provider_service()
    result = asyncio.run(service.generate("POST /api/v1/orders", "Creates a new order and reserves stock."))
    assert result.ai_generated is False
    assert result.target == "POST /api/v1/orders"
    assert "Functional:" in result.generated_text
    assert "Negative:" in result.generated_text
    assert "Regression:" in result.generated_text
    assert "API:" in result.generated_text
    assert "SQL Validation:" in result.generated_text
    assert set(result.test_types) == {"functional", "negative", "regression", "api", "sql"}


def test_generate_default_test_types_when_none_given():
    service = _no_provider_service()
    result = asyncio.run(service.generate("GET /health"))
    assert set(result.test_types) == {"functional", "negative", "regression", "api", "sql"}


def test_generate_filters_to_requested_test_types_only():
    service = _no_provider_service()
    result = asyncio.run(service.generate("POST /api/v1/orders", test_types=["functional", "negative"]))
    assert result.test_types == ("functional", "negative")
    assert "Functional:" in result.generated_text
    assert "Negative:" in result.generated_text
    assert "Regression:" not in result.generated_text


def test_generate_unknown_test_types_fall_back_to_default():
    service = _no_provider_service()
    result = asyncio.run(service.generate("POST /api/v1/orders", test_types=["not_a_real_type"]))
    assert set(result.test_types) == {"functional", "negative", "regression", "api", "sql"}


def test_generate_uses_ai_when_provider_configured():
    provider = _StubProvider("AI-written test cases grounded in target/context.")
    service = QAAssistantService(_StubProviderManager(provider=provider))
    result = asyncio.run(service.generate("POST /api/v1/orders", "Creates an order."))
    assert result.ai_generated is True
    assert result.generated_text == "AI-written test cases grounded in target/context."


def test_generate_falls_back_on_provider_failure():
    service = QAAssistantService(_StubProviderManager(provider=_FailingProvider()))
    result = asyncio.run(service.generate("POST /api/v1/orders", "Creates an order."))
    assert result.ai_generated is False
    assert "Functional:" in result.generated_text
