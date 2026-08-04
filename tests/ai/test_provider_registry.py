"""
Tests for ai/providers/registry.py — ProviderRegistry register/get/list.
"""

import pytest

from ai.core.exceptions import AIProviderNotFoundError
from ai.providers.base import BaseProvider
from ai.providers.registry import ProviderRegistry


class _FakeProvider(BaseProvider):
    name = "fake"

    def __init__(self, configured=False):
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    async def complete(self, prompt: str, **kwargs) -> dict:
        raise NotImplementedError


def test_registry_starts_empty():
    registry = ProviderRegistry()
    assert registry.list_providers() == []
    assert registry.list_configured_providers() == []


def test_register_and_get():
    registry = ProviderRegistry()
    provider = _FakeProvider(configured=True)
    registry.register(provider)
    assert registry.list_providers() == ["fake"]
    assert registry.get_provider("fake") is provider


def test_list_configured_providers_only_includes_configured():
    registry = ProviderRegistry()
    registry.register(_FakeProvider(configured=False))
    assert registry.list_providers() == ["fake"]
    assert registry.list_configured_providers() == []


def test_get_unregistered_provider_raises():
    registry = ProviderRegistry()
    with pytest.raises(AIProviderNotFoundError):
        registry.get_provider("does_not_exist")
