"""
Tests for centralized exception handling on the AI API Layer: every
error response must be the same {"error", "detail", "request_id"} shape
the rest of OMS360 uses (app/core/exceptions.py's global handler), with
no internal stack trace ever exposed - and AIInvalidCapabilityError
(the one Sprint-3-owned exception) as a plain Python object.
"""

import pytest

from ai.core.exceptions import AIInvalidCapabilityError, AIProviderNotFoundError
from app.core.exceptions import OMSBusinessError


def test_ai_invalid_capability_error_is_an_oms_business_error():
    assert issubclass(AIInvalidCapabilityError, OMSBusinessError)
    exc = AIInvalidCapabilityError("bogus", ("rag_enabled", "mcp_enabled"))
    assert exc.status_code == 400
    assert exc.error_code == "ai_invalid_capability"
    assert "bogus" in exc.detail
    assert "rag_enabled" in exc.detail


def test_ai_provider_not_found_error_is_an_oms_business_error():
    assert issubclass(AIProviderNotFoundError, OMSBusinessError)
    exc = AIProviderNotFoundError("not_real")
    assert exc.status_code == 404
    assert exc.error_code == "ai_provider_not_found"


def test_config_error_response_has_the_standard_three_fields_and_no_stack_trace(client):
    resp = client.get("/api/v1/ai/config", params={"capability": "bogus"})
    body = resp.json()
    assert set(body.keys()) == {"error", "detail", "request_id"}
    assert "Traceback" not in body["detail"]
    assert "File \"" not in body["detail"]


def test_providers_error_response_has_the_standard_three_fields_and_no_stack_trace(client):
    resp = client.get("/api/v1/ai/providers", params={"name": "not_real"})
    body = resp.json()
    assert set(body.keys()) == {"error", "detail", "request_id"}
    assert "Traceback" not in body["detail"]


def test_validation_error_response_shape_matches_app_wide_convention(client):
    resp = client.get("/api/v1/ai/config", params={"capability": ""})
    body = resp.json()
    assert body["error"] == "validation_error"
    assert "request_id" in body
