"""
Tests for ai/services/health_service.py — AIHealthService.check().
"""

from ai.providers.base import BaseProvider
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.health_service import AIHealthService


class _FakeProvider(BaseProvider):
    def __init__(self, name, configured):
        self.name = name
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    async def complete(self, prompt: str, **kwargs) -> dict:
        raise NotImplementedError


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    return RuntimeConfiguration(**base)


def test_healthy_true_when_no_validation_errors():
    service = AIHealthService(_runtime_config(), ValidationResult(), ProviderRegistry())
    report = service.check()
    assert report.healthy is True
    assert report.errors == []


def test_healthy_false_when_validation_errors_present():
    validation = ValidationResult(errors=["AI_ENABLED is true but no AI_API_KEY is configured."])
    service = AIHealthService(_runtime_config(ai_enabled=True), validation, ProviderRegistry())
    report = service.check()
    assert report.healthy is False
    assert len(report.errors) == 1


def test_configured_and_unconfigured_providers_partitioned_correctly():
    registry = ProviderRegistry()
    registry.register(_FakeProvider("openai", configured=True))
    registry.register(_FakeProvider("ollama", configured=False))
    service = AIHealthService(_runtime_config(), ValidationResult(), registry)
    report = service.check()
    assert report.configured_providers == ["openai"]
    assert report.unconfigured_providers == ["ollama"]
