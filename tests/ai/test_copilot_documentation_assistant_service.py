"""
Tests for ai/copilot/documentation_assistant_service.py —
DocumentationAssistantService.generate() in both the deterministic-
template (no provider) and AI-generated (stub provider) paths.
"""

import asyncio

from ai.copilot.documentation_assistant_service import DocumentationAssistantService
from ai.copilot.provider_manager import AIProviderManager, ProviderSelection
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
    return DocumentationAssistantService(AIProviderManager(ProviderRegistry()))


def test_generate_no_provider_uses_deterministic_template():
    service = _no_provider_service()
    facts = "- Added AI Root Cause Analysis\n- Added AI QA Assistant\n"
    result = asyncio.run(service.generate("sprint_summary", facts, title="Sprint 2"))
    assert result.ai_generated is False
    assert result.doc_type == "sprint_summary"
    assert result.title == "Sprint 2"
    assert "Added AI Root Cause Analysis" in result.generated_text
    assert "Added AI QA Assistant" in result.generated_text


def test_generate_never_invents_facts_not_supplied():
    service = _no_provider_service()
    result = asyncio.run(service.generate("readme_section", "- Only fact A", title=""))
    assert "Only fact A" in result.generated_text
    assert "fact B" not in result.generated_text.lower()


def test_generate_empty_facts_produces_placeholder():
    service = _no_provider_service()
    result = asyncio.run(service.generate("release_notes", "", title=""))
    assert result.ai_generated is False
    assert "No facts" in result.generated_text


def test_generate_uses_ai_when_provider_configured():
    provider = _StubProvider("AI-polished prose grounded strictly in the given facts.")
    service = DocumentationAssistantService(_StubProviderManager(provider=provider))
    result = asyncio.run(service.generate("api_docs", "- POST /orders creates an order"))
    assert result.ai_generated is True
    assert result.generated_text == "AI-polished prose grounded strictly in the given facts."


def test_generate_falls_back_on_provider_failure():
    service = DocumentationAssistantService(_StubProviderManager(provider=_FailingProvider()))
    result = asyncio.run(service.generate("readme_section", "- Some real fact"))
    assert result.ai_generated is False
    assert "Some real fact" in result.generated_text
