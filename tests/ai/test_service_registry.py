"""
Tests for ai/services/registry.py — ServiceRegistry register/get/list.
"""

import pytest

from ai.core.exceptions import AIServiceNotFoundError
from ai.services.registry import ServiceRegistry


def test_registry_starts_empty():
    registry = ServiceRegistry()
    assert registry.list_services() == []


def test_register_and_get():
    registry = ServiceRegistry()
    sentinel = object()
    registry.register("my_service", sentinel)
    assert registry.list_services() == ["my_service"]
    assert registry.get("my_service") is sentinel


def test_get_unregistered_service_raises():
    registry = ServiceRegistry()
    with pytest.raises(AIServiceNotFoundError):
        registry.get("does_not_exist")


def test_registering_same_name_twice_overwrites():
    registry = ServiceRegistry()
    registry.register("svc", "first")
    registry.register("svc", "second")
    assert registry.get("svc") == "second"
