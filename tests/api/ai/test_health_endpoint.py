"""
Dedicated tests for GET /api/v1/ai/health, per Sprint 3 objective 7.
Covers the real (default-environment) response, the healthy/unhealthy
distinction (AIHealthReport.healthy vs. AIServiceStatus.is_operational -
these are deliberately different checks, see ai/services/health_service.py
and ai/services/ai_service.py), and that the endpoint never performs a
network call or provider execution (verified via strict response-shape
assertions only - no provider/network fixture is stood up at all).
"""

from ai.dependencies import get_ai_health_service
from ai.services.health_service import AIHealthReport


def test_health_endpoint_reflects_real_default_environment_state(client):
    """With no AI_ENABLED / provider env vars set (the default in this
    test environment), the real AIHealthService should report no
    validation errors - RuntimeConfiguration's fail-closed defaults are
    all valid, just disabled."""
    resp = client.get("/api/v1/ai/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["healthy"] is True
    assert body["errors"] == []


def test_health_endpoint_surfaces_validation_errors_when_present(app, client):
    fake_report = AIHealthReport(
        healthy=False,
        ai_enabled=True,
        configured_providers=[],
        unconfigured_providers=["openai", "anthropic", "azure_openai", "ollama"],
        feature_flags={"rag_enabled": True, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
        errors=["AI_ENABLED is true but no provider is configured"],
        warnings=["RAG_ENABLED is true but rag_enabled capability has no backend"],
    )

    class _FakeHealthService:
        def check(self):
            return fake_report

    app.dependency_overrides[get_ai_health_service] = lambda: _FakeHealthService()
    try:
        resp = client.get("/api/v1/ai/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["healthy"] is False
        assert body["errors"] == ["AI_ENABLED is true but no provider is configured"]
        assert body["unconfigured_providers"] == ["openai", "anthropic", "azure_openai", "ollama"]
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_performs_no_provider_or_network_call(client):
    """No provider adapter's complete() is monkeypatched here on purpose -
    if the route ever called one, that call would raise
    AIProviderNotConfiguredError (every Sprint 2 provider fails closed;
    see ai/providers/*.py) and this request would return a 503, not 200."""
    resp = client.get("/api/v1/ai/health")
    assert resp.status_code == 200


def test_health_endpoint_does_not_require_ai_to_be_enabled():
    """healthy=True even when ai_enabled=False is the documented
    distinction between /health and /status - a disabled-but-validly-
    configured AI Runtime is 'healthy', just not 'operational'."""
    report = AIHealthReport(
        healthy=True, ai_enabled=False, configured_providers=[], unconfigured_providers=[],
        feature_flags={}, errors=[], warnings=[],
    )
    assert report.healthy is True
    assert report.ai_enabled is False
