"""
Tests for ai/providers/health.py — ProviderHealthChecker performs a live
call-through probe, distinct from AIHealthService's configuration-only
check (see tests/ai/test_health_service.py).
"""

import asyncio

from ai.core.exceptions import AIProviderCallFailedError
from ai.providers.base import BaseProvider
from ai.providers.health import ProviderHealthChecker
from ai.providers.mock_provider import MockAIProvider


class _RaisingProvider(BaseProvider):
    name = "raising"

    def is_configured(self) -> bool:
        return True

    async def complete(self, prompt: str, **kwargs) -> dict:
        raise AIProviderCallFailedError(self.name, "boom")


def test_check_reports_not_configured_without_calling_complete():
    provider = MockAIProvider(always_configured=False)
    result = asyncio.run(ProviderHealthChecker().check(provider))
    assert result.provider == "mock"
    assert result.configured is False
    assert result.reachable is False
    assert "not configured" in result.error.lower()


def test_check_reports_reachable_true_for_healthy_mock_provider():
    result = asyncio.run(ProviderHealthChecker().check(MockAIProvider()))
    assert result.configured is True
    assert result.reachable is True
    assert result.error == ""
    assert result.latency_ms >= 0


def test_check_reports_reachable_false_when_complete_raises():
    result = asyncio.run(ProviderHealthChecker().check(_RaisingProvider()))
    assert result.configured is True
    assert result.reachable is False
    assert "boom" in result.error


def test_check_reports_reachable_false_for_mock_simulating_failure():
    result = asyncio.run(ProviderHealthChecker().check(MockAIProvider(simulate_failure=True)))
    assert result.configured is True
    assert result.reachable is False
    assert result.error != ""


def test_check_all_returns_one_result_per_provider():
    providers = [MockAIProvider(), MockAIProvider(always_configured=False)]
    results = asyncio.run(ProviderHealthChecker().check_all(providers))
    assert len(results) == 2
    assert results[0].reachable is True
    assert results[1].configured is False
