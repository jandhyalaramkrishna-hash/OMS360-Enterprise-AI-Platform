"""
Tests for ai/core/exceptions.py — every AI exception must subclass the
existing OMSBusinessError so it gets the standard JSON error response.
"""

from app.core.exceptions import OMSBusinessError

from ai.core.exceptions import (
    AIAgentNotRegisteredError,
    AIFeatureDisabledError,
    AIProviderNotConfiguredError,
    AIServiceError,
    AIToolNotFoundError,
)


def test_all_ai_exceptions_subclass_oms_business_error():
    for exc_cls in (
        AIServiceError,
        AIFeatureDisabledError,
        AIProviderNotConfiguredError,
        AIToolNotFoundError,
        AIAgentNotRegisteredError,
    ):
        assert issubclass(exc_cls, OMSBusinessError)


def test_ai_feature_disabled_error_message_with_capability():
    exc = AIFeatureDisabledError("rag_enabled")
    assert "rag_enabled" in exc.detail
    assert exc.status_code == 403


def test_ai_feature_disabled_error_message_without_capability():
    exc = AIFeatureDisabledError()
    assert "disabled" in exc.detail.lower()


def test_ai_tool_not_found_error_carries_tool_name():
    exc = AIToolNotFoundError("weather_lookup")
    assert exc.tool_name == "weather_lookup"
    assert "weather_lookup" in exc.detail
    assert exc.status_code == 404


def test_ai_agent_not_registered_error_with_and_without_name():
    assert "planner" in AIAgentNotRegisteredError("planner").detail
    assert "No agents" in AIAgentNotRegisteredError().detail


def test_ai_provider_not_configured_default_message():
    exc = AIProviderNotConfiguredError()
    assert exc.status_code == 503
    assert "AI_PROVIDER" in exc.detail or "provider" in exc.detail.lower()
