"""
Shared fixtures for tests/api/ai/.

Builds a minimal FastAPI app that mirrors exactly how app/main.py wires
the AI API Layer - the same register_exception_handlers(app) call, the
same app.api.ai.router.router - without booting the rest of the real
application (orders/inventory/dashboard/kafka/database), which these
tests have no need to touch. This is standard FastAPI router-testing
practice (test a router via a fresh host app), not a stand-in for the
real app: every dependency, exception, and response model exercised
below is the actual Sprint 2/Sprint 3 production code.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers
from app.api.ai.router import router as ai_router

from ai.metrics import get_ai_metrics


@pytest.fixture()
def app():
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(ai_router)
    return test_app


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_ai_metrics():
    """AIMetrics is a process-lifetime singleton (ai/metrics.py) - reset
    it before every test so metrics assertions don't depend on test
    execution order."""
    get_ai_metrics().reset()
    yield
    get_ai_metrics().reset()
