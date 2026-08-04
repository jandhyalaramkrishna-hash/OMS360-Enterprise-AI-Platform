"""
Tests for the Sprint 9 addition to app/api/ai/router.py — GET
/api/v1/ai/platform/health, against the real Sprint 1-9 AI Runtime
singletons (ai/dependencies.py), exactly like tests/api/ai/test_routes.py
does for the six Sprint 3 routes. This route live-probes every registered
MCP tool and agent (deterministic, in-process mocks - no network/database
access), so, unlike the Sprint 3 routes, it is not purely read-only, but
it still makes zero real provider/LLM/Kafka/database call.
"""


def test_platform_health_route_returns_200_and_expected_shape(client):
    resp = client.get("/api/v1/ai/platform/health")
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "overall_healthy", "runtime_healthy", "ai_enabled", "feature_flags",
        "providers", "mcp_tools", "agents", "metrics", "errors", "warnings",
    ):
        assert key in body


def test_platform_health_route_reports_every_mcp_tool_and_agent(client):
    resp = client.get("/api/v1/ai/platform/health")
    body = resp.json()
    tool_names = {t["tool_name"] for t in body["mcp_tools"]}
    agent_names = {a["agent_name"] for a in body["agents"]}
    assert tool_names == {"order_lookup", "inventory_lookup", "delivery_status_lookup", "kitchen_status_lookup"}
    assert agent_names == {
        "order_agent", "inventory_agent", "kitchen_agent",
        "delivery_agent", "customer_support_agent", "analytics_agent",
    }
    assert all(t["healthy"] for t in body["mcp_tools"])
    assert all(a["healthy"] for a in body["agents"])


def test_platform_health_route_reports_the_mock_provider_as_configured_and_reachable(client):
    resp = client.get("/api/v1/ai/platform/health")
    body = resp.json()
    mock_entry = next(p for p in body["providers"] if p["provider"] == "mock")
    assert mock_entry["configured"] is True
    assert mock_entry["reachable"] is True


def test_platform_health_route_does_not_require_ai_enabled(client):
    # This route stays reachable regardless of AI_ENABLED, mirroring
    # GET /health's existing behavior - it is a diagnostic, not a
    # capability-gated feature.
    resp = client.get("/api/v1/ai/platform/health")
    assert resp.status_code == 200


def test_platform_health_route_is_present_in_the_openapi_schema(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/v1/ai/platform/health" in schema["paths"]
    operation = schema["paths"]["/api/v1/ai/platform/health"]["get"]
    assert operation.get("summary")
    assert operation.get("description")
    assert "200" in operation["responses"]
