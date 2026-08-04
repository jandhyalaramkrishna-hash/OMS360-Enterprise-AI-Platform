"""
Tests for ai/copilot/root_cause_service.py — RootCauseAnalysisService's
analyze_failed_orders()/analyze_duplicate_orders() against a real
(SQLite, in-memory) database, plus the AI-elaboration guardrail using a
stub provider (no real network call).

Async methods are driven via asyncio.run() inside plain `def test_...`
functions, matching this project's existing convention (no
pytest-asyncio - see tests/ai/test_copilot_business_qa_service.py).
"""

import asyncio
import datetime as dt

import pytest

from app import models
from app.core.enums import OrderStatus, PaymentStatus

from ai.copilot.provider_manager import AIProviderManager, ProviderSelection
from ai.copilot.root_cause_service import RootCauseAnalysisService
from ai.providers.registry import ProviderRegistry


class _StubProvider:
    name = "stub"

    def __init__(self, text):
        self._text = text

    async def complete(self, prompt: str, **kwargs) -> dict:
        return {"content": self._text}


class _FailingProvider:
    name = "failing"

    async def complete(self, prompt, **kwargs):
        raise RuntimeError("simulated provider failure")


class _StubProviderManager:
    def __init__(self, provider=None):
        self._selection = ProviderSelection(provider=provider, source="auto", reasoning_available=provider is not None)

    def get_active_provider(self):
        return self._selection


@pytest.fixture()
def service_no_provider():
    return RootCauseAnalysisService(AIProviderManager(ProviderRegistry()))


def test_analyze_failed_orders_no_data_is_not_an_error(copilot_db, service_no_provider):
    result = asyncio.run(service_no_provider.analyze_failed_orders(copilot_db))
    assert result.total_count == 0
    assert result.top_reasons == ()
    assert "no failed orders" in result.explanation_text.lower()
    assert result.ai_generated is False


def test_analyze_failed_orders_groups_by_reason(copilot_db, service_no_provider):
    now = dt.datetime.utcnow()
    copilot_db.add_all([
        models.FailedOrder(order_id="F-1", transaction_id="TXN-F1", reason="Payment gateway timeout", failed_at=now),
        models.FailedOrder(order_id="F-2", transaction_id="TXN-F2", reason="Payment gateway timeout", failed_at=now),
        models.FailedOrder(order_id="F-3", transaction_id="TXN-F3", reason="Insufficient inventory stock", failed_at=now),
    ])
    copilot_db.commit()

    result = asyncio.run(service_no_provider.analyze_failed_orders(copilot_db))
    assert result.total_count == 3
    assert result.ai_generated is False
    top = result.top_reasons[0]
    assert top.reason == "Payment gateway timeout"
    assert top.count == 2
    assert "Payment gateway timeout" in result.explanation_text
    assert "2 occurrence" in result.explanation_text
    # Payment-flavored reason should pattern-match to payment-specific steps.
    assert any("payment_service" in s for s in result.investigation_steps)


def test_analyze_failed_orders_uses_ai_when_provider_configured(copilot_db):
    copilot_db.add(models.FailedOrder(order_id="F-1", transaction_id="TXN-F1", reason="Kafka timeout", failed_at=dt.datetime.utcnow()))
    copilot_db.commit()

    provider = _StubProvider("AI-written explanation grounded in the given facts.")
    service = RootCauseAnalysisService(_StubProviderManager(provider=provider))
    result = asyncio.run(service.analyze_failed_orders(copilot_db))
    assert result.ai_generated is True
    assert result.explanation_text == "AI-written explanation grounded in the given facts."
    assert result.investigation_steps  # baseline deterministic steps carried through


def test_analyze_failed_orders_falls_back_on_provider_failure(copilot_db):
    copilot_db.add(models.FailedOrder(order_id="F-1", transaction_id="TXN-F1", reason="Unknown error", failed_at=dt.datetime.utcnow()))
    copilot_db.commit()

    service = RootCauseAnalysisService(_StubProviderManager(provider=_FailingProvider()))
    result = asyncio.run(service.analyze_failed_orders(copilot_db))
    assert result.ai_generated is False
    assert "1 failed order" in result.explanation_text


def test_analyze_duplicate_orders_no_data_is_not_an_error(copilot_db, service_no_provider):
    result = asyncio.run(service_no_provider.analyze_duplicate_orders(copilot_db))
    assert result.total_count == 0
    assert result.examples == ()
    assert "no duplicate order" in result.explanation_text.lower()
    assert result.ai_generated is False


def test_analyze_duplicate_orders_correlates_to_original_order(copilot_db, service_no_provider):
    copilot_db.add(models.OrdersMaster(
        order_id="ORD-1", transaction_id="TXN-1", customer_name="Alice", customer_id="CUST-1",
        mobile="9999999999", grand_total=100.0, total_amount=100.0,
        payment_status=PaymentStatus.PAID.value, order_status=OrderStatus.RECEIVED.value,
        created_at=dt.datetime.utcnow(),
    ))
    copilot_db.commit()
    copilot_db.add(models.DuplicateOrder(order_id="DUP-1", transaction_id="TXN-1", detected_at=dt.datetime.utcnow()))
    copilot_db.commit()

    result = asyncio.run(service_no_provider.analyze_duplicate_orders(copilot_db))
    assert result.total_count == 1
    assert len(result.examples) == 1
    example = result.examples[0]
    assert example["transaction_id"] == "TXN-1"
    assert "ORD-1" in example["outcome"]
    assert "RECEIVED" in example["outcome"]


def test_analyze_duplicate_orders_correlates_to_failed_original(copilot_db, service_no_provider):
    copilot_db.add(models.FailedOrder(order_id="F-1", transaction_id="TXN-2", reason="Payment failed", failed_at=dt.datetime.utcnow()))
    copilot_db.commit()
    copilot_db.add(models.DuplicateOrder(order_id="DUP-2", transaction_id="TXN-2", detected_at=dt.datetime.utcnow()))
    copilot_db.commit()

    result = asyncio.run(service_no_provider.analyze_duplicate_orders(copilot_db))
    example = result.examples[0]
    assert "failed" in example["outcome"].lower()
    assert "F-1" in example["outcome"]
