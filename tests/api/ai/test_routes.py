"""
Tests for the six AI API Layer routes - basic 200 responses and response
shape, against the real Sprint 2 AI Runtime singletons (ai/dependencies.py).
No provider is ever called, no request body is sent - these are read-only
GET endpoints.

Sprint 4 note: GET /api/v1/ai/providers reads from the same shared
ai.dependencies._provider_registry singleton that ai/services/factory.py's
ServiceFactory.build_provider_registry() populates - which now includes a
fifth provider, "mock" (ai.providers.mock_provider.MockAIProvider), added
by ai.providers.factory.ProviderFactory. This route itself was not
modified; test_providers_route_lists_all_known_providers below was updated
from its Sprint 2 four-provider expectation to five, since it is asserting
on real, shared state rather than anything mocked.
"""


def test_health_route_returns_200_and_expected_shape(client):
    resp = client.get("/api/v1/ai/health")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("healthy", "ai_enabled", "configured_providers", "unconfigured_providers", "feature_flags",
                "errors", "warnings"):
        assert key in body


def test_config_route_returns_200_and_expected_shape(client):
    resp = client.get("/api/v1/ai/config")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("ai_enabled", "provider_name", "provider_api_key_configured", "feature_flags",
                "validation_errors", "validation_warnings"):
        assert key in body
    assert body["capability_enabled"] is None  # not requested


def test_config_route_with_valid_capability_sets_capability_enabled(client):
    resp = client.get("/api/v1/ai/config", params={"capability": "rag_enabled"})
    assert resp.status_code == 200
    assert resp.json()["capability_enabled"] is False  # AI_ENABLED unset by default -> disabled


def test_providers_route_lists_all_known_providers(client):
    resp = client.get("/api/v1/ai/providers")
    assert resp.status_code == 200
    body = resp.json()
    names = sorted(p["name"] for p in body["providers"])
    assert names == ["anthropic", "azure_openai", "mock", "ollama", "openai"]
    assert body["total_count"] == 5


def test_providers_route_lookup_by_name(client):
    resp = client.get("/api/v1/ai/providers", params={"name": "openai"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "openai"
    assert "required_env_vars" in body


def test_features_route_returns_200_and_expected_shape(client):
    resp = client.get("/api/v1/ai/features")
    assert resp.status_code == 200
    body = resp.json()
    assert "ai_enabled" in body
    assert set(body["feature_flags"].keys()) == {"rag_enabled", "mcp_enabled", "agents_enabled", "evals_enabled"}


def test_metrics_route_returns_200_and_zeroed_counters(client):
    resp = client.get("/api/v1/ai/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_count"] == 0
    assert body["response_count"] == 0
    assert body["error_count"] == 0
    assert body["token_usage_total"] == 0
    assert body["provider_latency_ms"] == {}


def test_status_route_returns_200_and_expected_shape(client):
    resp = client.get("/api/v1/ai/status")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("ai_enabled", "is_operational", "capability_flags", "configured_providers",
                "validation_errors", "validation_warnings"):
        assert key in body
