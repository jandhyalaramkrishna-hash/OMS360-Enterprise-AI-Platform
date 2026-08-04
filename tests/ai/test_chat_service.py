"""
Tests for ai/services/chat_service.py — AIChatService.send_message() and
health_check()/health_check_all(), the first component in this project
whose call chain actually reaches a provider's complete() and returns a
real (simulated, via MockAIProvider) result.
"""

import asyncio

import pytest

from ai.core.exceptions import (
    AIChatInvalidRequestError,
    AIFeatureDisabledError,
    AIProviderCallFailedError,
    AIProviderNotConfiguredError,
)
from ai.metrics import AIMetrics
from ai.providers.health import ProviderHealthChecker
from ai.providers.mock_provider import MockAIProvider
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.ai_service import AIService
from ai.services.chat_service import AIChatService, ChatResult


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    return RuntimeConfiguration(**base)


def _make_service(ai_enabled=True, provider_name="mock", registry=None, metrics=None):
    registry = registry if registry is not None else ProviderRegistry()
    if not registry.list_providers():
        registry.register(MockAIProvider())
    ai_service = AIService(
        _runtime_config(ai_enabled=ai_enabled, provider_name=provider_name, provider_api_key_configured=True),
        ValidationResult(),
        registry,
    )
    return AIChatService(ai_service, registry, ProviderHealthChecker(), metrics or AIMetrics())


def test_send_message_returns_chat_result_from_mock_provider():
    metrics = AIMetrics()
    service = _make_service(metrics=metrics)
    result = asyncio.run(service.send_message("How long until my order arrives?"))
    assert isinstance(result, ChatResult)
    assert result.provider == "mock"
    assert result.is_mock is True
    assert "How long until my order arrives?" in result.content
    snapshot = metrics.snapshot()
    assert snapshot.request_count == 1
    assert snapshot.response_count == 1
    assert snapshot.error_count == 0
    assert "mock" in snapshot.provider_latency_ms


def test_send_message_rejects_blank_message():
    service = _make_service()
    with pytest.raises(AIChatInvalidRequestError):
        asyncio.run(service.send_message("   "))


def test_send_message_rejects_blank_message_even_when_ai_disabled():
    service = _make_service(ai_enabled=False)
    with pytest.raises(AIChatInvalidRequestError):
        asyncio.run(service.send_message(""))


def test_send_message_raises_when_ai_disabled():
    service = _make_service(ai_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.send_message("hello"))


def test_send_message_raises_when_no_provider_selected():
    registry = ProviderRegistry()
    registry.register(MockAIProvider())
    service = _make_service(provider_name="", registry=registry)
    with pytest.raises(AIProviderNotConfiguredError):
        asyncio.run(service.send_message("hello"))


def test_send_message_explicit_provider_name_overrides_selection():
    registry = ProviderRegistry()
    registry.register(MockAIProvider())
    service = _make_service(provider_name="", registry=registry)
    result = asyncio.run(service.send_message("hello", provider_name="mock"))
    assert result.provider == "mock"


def test_send_message_raises_when_selected_provider_not_configured():
    registry = ProviderRegistry()
    registry.register(MockAIProvider(always_configured=False))
    service = _make_service(registry=registry)
    with pytest.raises(AIProviderNotConfiguredError):
        asyncio.run(service.send_message("hello"))


def test_send_message_records_error_and_propagates_on_provider_failure():
    registry = ProviderRegistry()
    registry.register(MockAIProvider(simulate_failure=True))
    metrics = AIMetrics()
    service = _make_service(registry=registry, metrics=metrics)
    with pytest.raises(AIProviderCallFailedError):
        asyncio.run(service.send_message("hello"))
    snapshot = metrics.snapshot()
    assert snapshot.request_count == 1
    assert snapshot.error_count == 1
    assert snapshot.response_count == 0


def test_health_check_delegates_to_selected_provider():
    service = _make_service()
    result = asyncio.run(service.health_check())
    assert result.provider == "mock"
    assert result.reachable is True


def test_health_check_explicit_provider_name():
    registry = ProviderRegistry()
    registry.register(MockAIProvider())
    service = _make_service(provider_name="", registry=registry)
    result = asyncio.run(service.health_check(provider_name="mock"))
    assert result.provider == "mock"


def test_health_check_all_covers_every_registered_provider():
    from ai.providers.factory import ProviderFactory

    registry = ProviderFactory.build_registry()
    service = _make_service(registry=registry)
    results = asyncio.run(service.health_check_all())
    assert {r.provider for r in results} == set(ProviderFactory.known_provider_names())
