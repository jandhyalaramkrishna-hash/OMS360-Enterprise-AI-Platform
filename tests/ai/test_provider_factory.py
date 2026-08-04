"""
Tests for ai/providers/factory.py — ProviderFactory owns provider
construction by name.
"""

import pytest

from ai.core.exceptions import AIProviderNotFoundError
from ai.providers.base import BaseProvider
from ai.providers.factory import ProviderFactory
from ai.providers.mock_provider import MockAIProvider
from ai.providers.registry import ProviderRegistry


def test_known_provider_names_includes_all_five():
    assert ProviderFactory.known_provider_names() == [
        "anthropic", "azure_openai", "mock", "ollama", "openai",
    ]


def test_create_returns_correct_provider_type():
    provider = ProviderFactory.create("mock")
    assert isinstance(provider, MockAIProvider)
    assert provider.name == "mock"


def test_create_returns_a_new_instance_each_time():
    a = ProviderFactory.create("mock")
    b = ProviderFactory.create("mock")
    assert a is not b


def test_create_raises_for_unknown_name():
    with pytest.raises(AIProviderNotFoundError):
        ProviderFactory.create("does_not_exist")


def test_create_all_returns_one_instance_of_each_known_provider():
    providers = ProviderFactory.create_all()
    names = sorted(p.name for p in providers)
    assert names == ["anthropic", "azure_openai", "mock", "ollama", "openai"]
    assert all(isinstance(p, BaseProvider) for p in providers)


def test_build_registry_returns_populated_registry():
    registry = ProviderFactory.build_registry()
    assert isinstance(registry, ProviderRegistry)
    assert registry.list_providers() == ["anthropic", "azure_openai", "mock", "ollama", "openai"]


def test_build_registry_mock_is_configured_by_default():
    registry = ProviderFactory.build_registry()
    assert "mock" in registry.list_configured_providers()
