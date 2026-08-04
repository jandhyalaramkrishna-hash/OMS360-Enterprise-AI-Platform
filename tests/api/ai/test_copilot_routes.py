"""
Tests for app/api/ai/copilot_router.py — the ten AI Copilot HTTP routes,
against a fresh, self-contained FastAPI test app (same standard
router-testing pattern as tests/api/ai/conftest.py already uses for the
Sprint 3 AI Runtime router: a real router, real dependencies, real
exception handling, without booting the full app/orders/kafka stack).

app.database.get_db is overridden with an in-memory SQLite session
(StaticPool - see tests/ai/conftest.py's copilot_db fixture docstring
for why that's required for :memory: SQLite specifically), seeded with a
small, realistic baseline. This exercises the real BusinessQAService /
ExecutiveSummaryService / BusinessInsightsService / AIProviderManager
singletons from ai.dependencies - nothing here is mocked except the
database backend itself.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.ai.copilot_router import router as copilot_router
from app.core.exceptions import register_exception_handlers
from app.database import Base, get_db

from ai.dependencies import get_copilot_runtime_config
from ai.runtime.config import RuntimeConfiguration

from tests.ai.conftest import seed_baseline


@pytest.fixture()
def db_session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    yield session_local
    engine.dispose()


@pytest.fixture()
def app(db_session_factory):
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(copilot_router)

    def _override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = _override_get_db
    return test_app


@pytest.fixture()
def seeded_client(app, db_session_factory):
    db = db_session_factory()
    seed_baseline(db)
    db.close()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_ask_matched_question_returns_200(seeded_client):
    resp = seeded_client.post("/api/v1/ai/copilot/ask", json={"question": "How many pending orders?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] is True
    assert body["intent"] == "pending_orders"
    assert body["answer_text"] == "There are 2 pending orders."
    assert body["value"] == 2
    # SQL must never appear in the /ask response itself.
    assert "sql" not in body


def test_ask_unmatched_question_returns_suggestions(seeded_client):
    resp = seeded_client.post("/api/v1/ai/copilot/ask", json={"question": "what's the weather?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] is False
    assert len(body["suggested_questions"]) == 6


def test_ask_blank_question_returns_422(client):
    resp = client.post("/api/v1/ai/copilot/ask", json={"question": ""})
    assert resp.status_code == 422


def test_ask_missing_question_field_returns_422(client):
    resp = client.post("/api/v1/ai/copilot/ask", json={})
    assert resp.status_code == 422


def test_intent_sql_endpoint(client):
    resp = client.get("/api/v1/ai/copilot/intents/pending_orders/sql")
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "pending_orders"
    assert "orders_master" in body["sql_text"]


def test_intent_sql_endpoint_unknown_intent_returns_404(client):
    resp = client.get("/api/v1/ai/copilot/intents/not_a_real_intent/sql")
    assert resp.status_code == 404
    assert resp.json()["error"] == "ai_copilot_intent_not_found"


def test_intent_explain_endpoint(client):
    resp = client.get("/api/v1/ai/copilot/intents/pending_orders/explain")
    assert resp.status_code == 200
    assert "orders_master" in resp.json()["explanation"]


def test_intent_related_tables_endpoint(client):
    resp = client.get("/api/v1/ai/copilot/intents/pending_orders/related-tables")
    assert resp.status_code == 200
    assert resp.json()["related_tables"] == ["orders_master"]


def test_intent_business_flow_endpoint(client):
    resp = client.get("/api/v1/ai/copilot/intents/pending_orders/business-flow")
    assert resp.status_code == 200
    assert resp.json()["business_flow"]


def test_questions_endpoint_lists_examples(client):
    resp = client.get("/api/v1/ai/copilot/questions")
    assert resp.status_code == 200
    assert len(resp.json()["questions"]) > 0


def test_business_insights_endpoint(seeded_client):
    resp = seeded_client.get("/api/v1/ai/copilot/business-insights")
    assert resp.status_code == 200
    insights = resp.json()["insights"]
    assert any(i["severity"] == "critical" for i in insights)  # the seeded OUT_OF_STOCK item


def test_provider_status_endpoint_defaults_to_deterministic(client, monkeypatch):
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    resp = client.get("/api/v1/ai/copilot/provider-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_provider"] is None
    assert body["source"] == "none_configured"
    assert body["reasoning_available"] is False
    assert body["copilot_enabled"] is True


def test_copilot_disabled_returns_403(app):
    def _disabled_config():
        return RuntimeConfiguration(
            ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
            provider_name="", provider_api_key_configured=False, feature_flags={}, copilot_enabled=False,
        )

    app.dependency_overrides[get_copilot_runtime_config] = _disabled_config
    disabled_client = TestClient(app, raise_server_exceptions=False)

    resp = disabled_client.post("/api/v1/ai/copilot/ask", json={"question": "How many pending orders?"})
    assert resp.status_code == 403
    assert resp.json()["error"] == "ai_copilot_disabled"

    resp2 = disabled_client.get("/api/v1/ai/copilot/business-insights")
    assert resp2.status_code == 403

    resp3 = disabled_client.get("/api/v1/ai/copilot/root-cause/failed-orders")
    assert resp3.status_code == 403

    resp4 = disabled_client.post("/api/v1/ai/copilot/qa-assistant/generate", json={"target": "GET /health"})
    assert resp4.status_code == 403

    resp5 = disabled_client.post("/api/v1/ai/copilot/docs-assistant/generate", json={"doc_type": "readme_section", "facts": "- x"})
    assert resp5.status_code == 403

    resp6 = disabled_client.get("/api/v1/ai/copilot/learning/topics")
    assert resp6.status_code == 403


def test_explain_endpoint_default_use_ai_true_without_provider_matches_deterministic(client):
    resp = client.get("/api/v1/ai/copilot/intents/pending_orders/explain")
    assert resp.status_code == 200
    resp_no_ai = client.get("/api/v1/ai/copilot/intents/pending_orders/explain?use_ai=false")
    assert resp_no_ai.status_code == 200
    assert resp.json()["explanation"] == resp_no_ai.json()["explanation"]


def test_root_cause_failed_orders_endpoint_empty(client):
    resp = client.get("/api/v1/ai/copilot/root-cause/failed-orders")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 0
    assert body["top_reasons"] == []
    assert body["ai_generated"] is False


def test_root_cause_failed_orders_endpoint_with_data(app, db_session_factory):
    import datetime as dt
    from app import models

    db = db_session_factory()
    db.add(models.FailedOrder(order_id="F-1", transaction_id="TXN-F1", reason="Payment gateway timeout", failed_at=dt.datetime.utcnow()))
    db.commit()
    db.close()
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/api/v1/ai/copilot/root-cause/failed-orders")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 1
    assert body["top_reasons"][0]["reason"] == "Payment gateway timeout"
    assert body["investigation_steps"]


def test_root_cause_duplicate_orders_endpoint_empty(client):
    resp = client.get("/api/v1/ai/copilot/root-cause/duplicate-orders")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 0
    assert body["examples"] == []


def test_qa_assistant_generate_endpoint(client):
    resp = client.post(
        "/api/v1/ai/copilot/qa-assistant/generate",
        json={"target": "POST /api/v1/orders", "context": "Creates a new order.", "test_types": ["functional", "negative"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target"] == "POST /api/v1/orders"
    assert body["test_types"] == ["functional", "negative"]
    assert body["ai_generated"] is False
    assert "Functional:" in body["generated_text"]


def test_qa_assistant_generate_endpoint_defaults_all_test_types(client):
    resp = client.post("/api/v1/ai/copilot/qa-assistant/generate", json={"target": "GET /health"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["test_types"]) == {"functional", "negative", "regression", "api", "sql"}


def test_docs_assistant_generate_endpoint(client):
    resp = client.post(
        "/api/v1/ai/copilot/docs-assistant/generate",
        json={"doc_type": "sprint_summary", "facts": "- Added AI Root Cause Analysis", "title": "Sprint 2"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["doc_type"] == "sprint_summary"
    assert body["title"] == "Sprint 2"
    assert body["ai_generated"] is False
    assert "Added AI Root Cause Analysis" in body["generated_text"]


def test_learning_topics_endpoint_lists_seven_topics(client):
    resp = client.get("/api/v1/ai/copilot/learning/topics")
    assert resp.status_code == 200
    topics = resp.json()["topics"]
    assert len(topics) == 7
    assert {"topic": "kafka", "title": "Kafka Event Processing"} in topics


def test_learning_topic_explain_endpoint(client):
    resp = client.get("/api/v1/ai/copilot/learning/topics/kafka")
    assert resp.status_code == 200
    body = resp.json()
    assert body["topic"] == "kafka"
    assert body["ai_generated"] is False
    assert "producer" in body["text"].lower()


def test_learning_topic_explain_endpoint_unknown_topic_returns_404(client):
    resp = client.get("/api/v1/ai/copilot/learning/topics/not_a_real_topic")
    assert resp.status_code == 404
    assert resp.json()["error"] == "ai_copilot_learning_topic_not_found"


def test_learning_ask_endpoint_matches_topic(client):
    resp = client.post("/api/v1/ai/copilot/learning/ask", json={"question": "How does inventory stock reservation work?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched_topic"] == "inventory"
