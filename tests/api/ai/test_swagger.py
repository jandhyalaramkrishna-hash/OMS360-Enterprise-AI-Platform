"""
Tests that all six AI API Layer endpoints expose complete OpenAPI/Swagger
documentation - Summary, Description, Response Model (schema reference),
and Status Codes - per Sprint 3 objective 5.
"""

import pytest

AI_PATHS = (
    "/api/v1/ai/health",
    "/api/v1/ai/config",
    "/api/v1/ai/providers",
    "/api/v1/ai/features",
    "/api/v1/ai/metrics",
    "/api/v1/ai/status",
)


@pytest.fixture()
def openapi_schema(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json()


def test_all_six_ai_paths_are_present_in_the_openapi_schema(openapi_schema):
    for path in AI_PATHS:
        assert path in openapi_schema["paths"], path


@pytest.mark.parametrize("path", AI_PATHS)
def test_each_endpoint_has_summary_description_and_200_response(openapi_schema, path):
    operation = openapi_schema["paths"][path]["get"]
    assert operation.get("summary"), f"{path} missing summary"
    assert operation.get("description"), f"{path} missing description"
    assert "200" in operation["responses"], f"{path} missing a 200 response"
    schema_200 = operation["responses"]["200"].get("content", {}).get("application/json", {}).get("schema")
    assert schema_200, f"{path} 200 response has no response model schema"


def test_config_endpoint_documents_its_error_status_codes(openapi_schema):
    responses = openapi_schema["paths"]["/api/v1/ai/config"]["get"]["responses"]
    assert "400" in responses
    assert "422" in responses


def test_providers_endpoint_documents_its_error_status_codes(openapi_schema):
    responses = openapi_schema["paths"]["/api/v1/ai/providers"]["get"]["responses"]
    assert "404" in responses
    assert "422" in responses


def test_ai_runtime_tag_present(openapi_schema):
    for path in AI_PATHS:
        assert "AI Runtime" in openapi_schema["paths"][path]["get"]["tags"]
