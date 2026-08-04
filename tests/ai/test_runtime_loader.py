"""
Tests for ai/runtime/loader.py — RuntimeConfigLoader caching and the
module-level singleton accessor.
"""

from ai.runtime.loader import RuntimeConfigLoader, get_runtime_config_loader


def test_load_caches_until_force_reload(monkeypatch):
    loader = RuntimeConfigLoader()
    monkeypatch.delenv("AI_ENABLED", raising=False)

    first = loader.load()
    assert first.ai_enabled is False

    monkeypatch.setenv("AI_ENABLED", "true")
    second = loader.load()  # no force_reload - should return the cached (stale) value
    assert second.ai_enabled is False
    assert second is first

    third = loader.load(force_reload=True)
    assert third.ai_enabled is True


def test_validation_available_without_explicit_load_call(monkeypatch):
    loader = RuntimeConfigLoader()
    monkeypatch.delenv("AI_ENABLED", raising=False)
    validation = loader.validation()
    assert validation.is_valid is True


def test_get_runtime_config_loader_is_a_singleton():
    assert get_runtime_config_loader() is get_runtime_config_loader()
