"""
Tests for ai/copilot/learning_assistant_service.py — LearningAssistantService's
list_topics()/explain_topic()/ask(), against the hand-written knowledge
base, plus the AI-elaboration guardrail using a stub provider.
"""

import asyncio

import pytest

from ai.copilot.learning_assistant_service import LearningAssistantService
from ai.copilot.provider_manager import AIProviderManager, ProviderSelection
from ai.core.exceptions import AICopilotLearningTopicNotFoundError
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


def _no_provider_service():
    return LearningAssistantService(AIProviderManager(ProviderRegistry()))


def test_list_topics_returns_all_seven_topics():
    service = _no_provider_service()
    topics = service.list_topics()
    keys = {t["topic"] for t in topics}
    assert keys == {"architecture", "kafka", "inventory", "kitchen", "delivery", "monitoring", "database"}


def test_explain_topic_no_provider_returns_hand_written_text():
    service = _no_provider_service()
    answer = asyncio.run(service.explain_topic("kafka"))
    assert answer.ai_generated is False
    assert "producer" in answer.text.lower()
    assert answer.title == "Kafka Event Processing"


def test_explain_topic_use_ai_false_returns_hand_written_text_even_with_provider():
    provider = _StubProvider("An LLM elaboration that should not be used.")
    service = LearningAssistantService(_StubProviderManager(provider=provider))
    answer = asyncio.run(service.explain_topic("kafka", use_ai=False))
    assert answer.ai_generated is False
    assert "producer" in answer.text.lower()


def test_explain_topic_uses_ai_when_provider_configured():
    provider = _StubProvider("Elaborated Kafka explanation grounded in the given facts.")
    service = LearningAssistantService(_StubProviderManager(provider=provider))
    answer = asyncio.run(service.explain_topic("kafka", use_ai=True))
    assert answer.ai_generated is True
    assert answer.text == "Elaborated Kafka explanation grounded in the given facts."


def test_explain_topic_falls_back_on_provider_failure():
    service = LearningAssistantService(_StubProviderManager(provider=_FailingProvider()))
    answer = asyncio.run(service.explain_topic("kafka", use_ai=True))
    assert answer.ai_generated is False
    assert "producer" in answer.text.lower()


def test_explain_unknown_topic_raises():
    service = _no_provider_service()
    with pytest.raises(AICopilotLearningTopicNotFoundError):
        asyncio.run(service.explain_topic("not_a_real_topic"))


def test_ask_matches_nearest_topic_by_keyword():
    service = _no_provider_service()
    answer = asyncio.run(service.ask("How does the kitchen cooking status work?"))
    assert answer.topic == "kitchen"


def test_ask_falls_back_to_architecture_when_unmatched():
    service = _no_provider_service()
    answer = asyncio.run(service.ask("what's the weather like today?"))
    assert answer.topic == "architecture"
