"""
Tests for validation on the AI API Layer's two query parameters:
GET /config?capability= and GET /providers?name=.

Covers: missing values (omitted - valid, optional), blank values (422,
FastAPI's own Query(min_length=1)), and invalid-but-non-blank values
(400/404, application-level validation in router.py).
"""


def test_config_capability_omitted_is_valid_and_optional(client):
    resp = client.get("/api/v1/ai/config")
    assert resp.status_code == 200
    assert resp.json()["capability_enabled"] is None


def test_config_capability_blank_returns_422(client):
    resp = client.get("/api/v1/ai/config", params={"capability": ""})
    assert resp.status_code == 422


def test_config_capability_unknown_value_returns_400(client):
    resp = client.get("/api/v1/ai/config", params={"capability": "not_a_real_flag"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "ai_invalid_capability"
    assert "not_a_real_flag" in body["detail"]


def test_config_capability_each_known_value_is_accepted(client):
    for capability in ("rag_enabled", "mcp_enabled", "agents_enabled", "evals_enabled"):
        resp = client.get("/api/v1/ai/config", params={"capability": capability})
        assert resp.status_code == 200, capability
        assert resp.json()["capability_enabled"] is not None


def test_providers_name_omitted_is_valid_and_optional(client):
    resp = client.get("/api/v1/ai/providers")
    assert resp.status_code == 200
    assert "providers" in resp.json()


def test_providers_name_blank_returns_422(client):
    resp = client.get("/api/v1/ai/providers", params={"name": ""})
    assert resp.status_code == 422


def test_providers_name_unregistered_returns_404(client):
    resp = client.get("/api/v1/ai/providers", params={"name": "not_a_real_provider"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "ai_provider_not_found"
