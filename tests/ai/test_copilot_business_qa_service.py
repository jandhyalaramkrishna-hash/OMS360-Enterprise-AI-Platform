"""
Tests for ai/copilot/business_qa_service.py — BusinessQAService.ask()
against a real (SQLite, in-memory) database, plus the "reword, never
invent" LLM guardrail using a stub provider (no real network call, no
mocking of the guardrail logic itself).

Async methods are driven via asyncio.run() inside plain `def test_...`
functions - the same pattern tests/ai/test_workflow_service.py and
tests/ai/test_chat_service.py already use, rather than pytest-asyncio
(not a project dependency - see requirements.txt).
"""

import asyncio

import pytest

from ai.copilot.business_qa_service import BusinessQAService
from ai.copilot.provider_manager import AIProviderManager, ProviderSelection
from ai.core.exceptions import AICopilotIntentNotFoundError, AICopilotInvalidQuestionError
from ai.providers.registry import ProviderRegistry

from tests.ai.conftest import seed_baseline


class _StubProvider:
    """A minimal stand-in for a real provider's complete() - returns a
    fixed reworded string rather than calling any network/LLM API."""

    name = "stub"

    def __init__(self, reworded_text):
        self._reworded_text = reworded_text

    async def complete(self, prompt: str, **kwargs) -> dict:
        return {"content": self._reworded_text}


class _StubProviderManager:
    """Stands in for AIProviderManager - returns a fixed ProviderSelection
    instead of consulting the real ProviderRegistry/environment."""

    def __init__(self, provider=None, source="auto"):
        self._selection = ProviderSelection(
            provider=provider, source=source, reasoning_available=provider is not None
        )

    def get_active_provider(self):
        return self._selection


@pytest.fixture()
def qa_service_no_provider():
    """Matches the default, zero-API-key baseline: an AIProviderManager
    over an empty/unconfigured registry, i.e. deterministic-only mode."""
    return BusinessQAService(AIProviderManager(ProviderRegistry()))


def test_ask_matched_question_returns_real_deterministic_answer(copilot_db, qa_service_no_provider):
    seed_baseline(copilot_db)
    result = asyncio.run(qa_service_no_provider.ask("How many pending orders?", copilot_db))
    assert result.matched is True
    assert result.intent == "pending_orders"
    assert result.answer_text == "There are 2 pending orders."
    assert result.value == 2
    assert result.reworded_by_ai is False
    assert result.active_provider is None


def test_ask_unmatched_question_returns_suggestions(copilot_db, qa_service_no_provider):
    seed_baseline(copilot_db)
    result = asyncio.run(qa_service_no_provider.ask("what's the weather like today?", copilot_db))
    assert result.matched is False
    assert result.intent is None
    assert result.value is None
    assert len(result.suggested_questions) == 6


def test_ask_blank_question_raises(copilot_db, qa_service_no_provider):
    with pytest.raises(AICopilotInvalidQuestionError):
        asyncio.run(qa_service_no_provider.ask("", copilot_db))
    with pytest.raises(AICopilotInvalidQuestionError):
        asyncio.run(qa_service_no_provider.ask("   ", copilot_db))


def test_get_sql_for_known_intent(copilot_db, qa_service_no_provider):
    sql = qa_service_no_provider.get_sql("pending_orders")
    assert "orders_master" in sql
    assert "RECEIVED" in sql


def test_get_sql_for_unknown_intent_raises(qa_service_no_provider):
    with pytest.raises(AICopilotIntentNotFoundError):
        qa_service_no_provider.get_sql("not_a_real_intent")


def test_get_related_tables_and_business_flow(qa_service_no_provider):
    assert qa_service_no_provider.get_related_tables("pending_orders") == ["orders_master"]
    assert "RECEIVED" in qa_service_no_provider.get_business_flow("pending_orders")


def test_get_explanation_grounds_in_sql_and_flow(qa_service_no_provider):
    explanation = qa_service_no_provider.get_explanation("pending_orders")
    assert "SELECT COUNT(*) FROM orders_master" in explanation
    assert "orders_master" in explanation


def test_reword_accepted_when_numbers_preserved(copilot_db):
    provider = _StubProvider("You currently have 2 orders waiting to be picked up by the kitchen.")
    service = BusinessQAService(_StubProviderManager(provider=provider))
    seed_baseline(copilot_db)
    result = asyncio.run(service.ask("How many pending orders?", copilot_db))
    assert result.matched is True
    assert result.reworded_by_ai is True
    assert result.active_provider == "stub"
    assert "2" in result.answer_text


def test_reword_rejected_when_provider_changes_the_number(copilot_db):
    # The guardrail (_numbers_preserved) must reject this and keep the
    # original, correct sentence - accuracy always wins over style.
    provider = _StubProvider("You currently have 99 orders waiting.")
    service = BusinessQAService(_StubProviderManager(provider=provider))
    seed_baseline(copilot_db)
    result = asyncio.run(service.ask("How many pending orders?", copilot_db))
    assert result.matched is True
    assert result.reworded_by_ai is False
    assert result.answer_text == "There are 2 pending orders."


def test_reword_failure_falls_back_to_deterministic_sentence(copilot_db):
    class _FailingProvider:
        name = "failing"

        async def complete(self, prompt, **kwargs):
            raise RuntimeError("simulated provider failure")

    service = BusinessQAService(_StubProviderManager(provider=_FailingProvider()))
    seed_baseline(copilot_db)
    result = asyncio.run(service.ask("How many pending orders?", copilot_db))
    assert result.matched is True
    assert result.reworded_by_ai is False
    assert result.answer_text == "There are 2 pending orders."


def test_get_explanation_async_no_provider_matches_deterministic_template(qa_service_no_provider):
    async_explanation = asyncio.run(qa_service_no_provider.get_explanation_async("pending_orders"))
    assert async_explanation == qa_service_no_provider.get_explanation("pending_orders")


def test_get_explanation_async_use_ai_false_matches_deterministic_template():
    provider = _StubProvider("An LLM-written explanation that should not be used.")
    service = BusinessQAService(_StubProviderManager(provider=provider))
    async_explanation = asyncio.run(service.get_explanation_async("pending_orders", use_ai=False))
    assert async_explanation == service.get_explanation("pending_orders")


def test_get_explanation_async_uses_ai_when_provider_configured():
    provider = _StubProvider("Enriched: counts RECEIVED rows in orders_master, grounded in the given SQL.")
    service = BusinessQAService(_StubProviderManager(provider=provider))
    result = asyncio.run(service.get_explanation_async("pending_orders", use_ai=True))
    assert result == "Enriched: counts RECEIVED rows in orders_master, grounded in the given SQL."


def test_get_explanation_async_falls_back_on_provider_failure():
    class _FailingProvider:
        name = "failing"

        async def complete(self, prompt, **kwargs):
            raise RuntimeError("simulated provider failure")

    service = BusinessQAService(_StubProviderManager(provider=_FailingProvider()))
    result = asyncio.run(service.get_explanation_async("pending_orders", use_ai=True))
    assert result == service.get_explanation("pending_orders")


def test_get_explanation_async_unknown_intent_raises(qa_service_no_provider):
    with pytest.raises(AICopilotIntentNotFoundError):
        asyncio.run(qa_service_no_provider.get_explanation_async("not_a_real_intent"))
