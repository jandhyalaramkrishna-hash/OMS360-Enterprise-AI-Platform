"""
Tests that the AI API Layer routes are genuinely wired via FastAPI
Depends(...) - not hardcoded calls to the ai/dependencies.py singletons -
by overriding each dependency with a fake and confirming the route
returns the fake's data instead of the real singleton's.
"""

from ai.dependencies import (
    get_ai_health_service,
    get_ai_metrics,
    get_ai_service,
    get_config_loader,
    get_provider_registry,
)
from ai.metrics import AIMetricsSnapshot


class _FakeHealthService:
    def check(self):
        from ai.services.health_service import AIHealthReport
        return AIHealthReport(
            healthy=False, ai_enabled=True, configured_providers=["fake_provider"],
            unconfigured_providers=[], feature_flags={}, errors=["fake error"], warnings=[],
        )


class _FakeAIService:
    def status(self):
        from ai.services.ai_service import AIServiceStatus
        return AIServiceStatus(
            ai_enabled=True, capability_flags={}, configured_providers=["fake_provider"],
            validation_errors=[], validation_warnings=[],
        )


class _FakeMetrics:
    def snapshot(self):
        return AIMetricsSnapshot(request_count=999, response_count=888, error_count=1,
                                  token_usage_total=42, provider_latency_ms={})


def test_health_route_uses_injected_health_service(app, client):
    app.dependency_overrides[get_ai_health_service] = lambda: _FakeHealthService()
    try:
        resp = client.get("/api/v1/ai/health")
        body = resp.json()
        assert body["healthy"] is False
        assert body["configured_providers"] == ["fake_provider"]
        assert body["errors"] == ["fake error"]
    finally:
        app.dependency_overrides.clear()


def test_status_route_uses_injected_ai_service(app, client):
    app.dependency_overrides[get_ai_service] = lambda: _FakeAIService()
    try:
        resp = client.get("/api/v1/ai/status")
        assert resp.json()["configured_providers"] == ["fake_provider"]
    finally:
        app.dependency_overrides.clear()


def test_metrics_route_uses_injected_metrics(app, client):
    app.dependency_overrides[get_ai_metrics] = lambda: _FakeMetrics()
    try:
        resp = client.get("/api/v1/ai/metrics")
        body = resp.json()
        assert body["request_count"] == 999
        assert body["token_usage_total"] == 42
    finally:
        app.dependency_overrides.clear()


def test_config_and_features_routes_depend_on_the_same_config_loader_provider():
    # Both routes list get_config_loader in their signature's Depends(...) -
    # confirmed by inspecting the router's dependant tree rather than only
    # by behavior, so a future refactor that silently drops the DI wiring
    # (e.g. replaces Depends(get_config_loader) with a direct singleton
    # call) fails this test even if the response still looks correct.
    from app.api.ai.router import router

    routes_by_path = {r.path: r for r in router.routes}
    for path in ("/api/v1/ai/config", "/api/v1/ai/features"):
        dependant = routes_by_path[path].dependant
        dep_calls = [d.call for d in dependant.dependencies]
        assert get_config_loader in dep_calls


def test_providers_route_depends_on_provider_registry_provider():
    from app.api.ai.router import router

    routes_by_path = {r.path: r for r in router.routes}
    dependant = routes_by_path["/api/v1/ai/providers"].dependant
    dep_calls = [d.call for d in dependant.dependencies]
    assert get_provider_registry in dep_calls
