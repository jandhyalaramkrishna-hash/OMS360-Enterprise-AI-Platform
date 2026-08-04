"""
Tests for ai/providers/mock_provider.py — MockAIProvider is the first
provider whose complete() actually returns a result (never touches the
network), and is fully controllable for testing the rest of the Provider
Framework.
"""

import asyncio

import pytest

from ai.core.exceptions import AIProviderCallFailedError
from ai.providers.base import BaseProvider
from ai.providers.mock_provider import MockAIProvider


def test_mock_provider_is_a_base_provider():
    assert isinstance(MockAIProvider(), BaseProvider)


def test_mock_provider_name_is_mock():
    assert MockAIProvider.name == "mock"


def test_mock_provider_requires_no_env_vars():
    assert MockAIProvider.required_env_vars == ()


def test_always_configured_by_default():
    assert MockAIProvider().is_configured() is True


def test_can_be_constructed_as_not_configured_for_tests():
    assert MockAIProvider(always_configured=False).is_configured() is False


def test_complete_returns_deterministic_structured_result():
    provider = MockAIProvider()
    result = asyncio.run(provider.complete("What is the ETA for order 42?"))
    assert result["provider"] == "mock"
    assert result["model"] == "mock-model-v1"
    assert "What is the ETA for order 42?" in result["content"]
    assert result["usage"]["total_tokens"] > 0


def test_complete_never_raises_when_not_simulating_failure():
    provider = MockAIProvider()
    # should not raise
    asyncio.run(provider.complete("hello"))


def test_complete_raises_ai_provider_call_failed_when_simulating_failure():
    provider = MockAIProvider(simulate_failure=True)
    with pytest.raises(AIProviderCallFailedError):
        asyncio.run(provider.complete("hello"))


def test_complete_respects_simulated_latency(monkeypatch):
    sleeps = []

    async def _fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    provider = MockAIProvider(simulated_latency_ms=50)
    asyncio.run(provider.complete("hello"))
    assert sleeps == [0.05]


def test_complete_handles_empty_prompt_without_raising():
    provider = MockAIProvider()
    result = asyncio.run(provider.complete(""))
    assert result["content"] == "[mock] "
