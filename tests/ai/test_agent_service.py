"""
Tests for ai/agents/agent_service.py — AgentService: capability-gated
run()/list_agents(), delegating to AgentOrchestrator.
"""

import asyncio

import pytest

from ai.agents.agent_service import AgentService
from ai.agents.base import AgentBase, AgentContext
from ai.agents.orchestrator import AgentOrchestrator
from ai.core.exceptions import AIFeatureDisabledError
from ai.providers.mock_provider import MockAIProvider
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.ai_service import AIService


class _EchoAgent(AgentBase):
    name = "echo"

    async def run(self, context: AgentContext) -> AgentContext:
        context.data["echoed"] = context.input
        return context


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    if "agents_enabled" in overrides:
        base["feature_flags"] = {**base["feature_flags"], "agents_enabled": overrides["agents_enabled"]}
    return RuntimeConfiguration(**base)


def _ai_service(ai_enabled=True, agents_enabled=True):
    registry = ProviderRegistry()
    registry.register(MockAIProvider())
    return AIService(_runtime_config(ai_enabled=ai_enabled, agents_enabled=agents_enabled), ValidationResult(), registry)


def _make_service(ai_enabled=True, agents_enabled=True):
    orchestrator = AgentOrchestrator()
    orchestrator.register(_EchoAgent())
    return AgentService(orchestrator, _ai_service(ai_enabled=ai_enabled, agents_enabled=agents_enabled))


def test_list_agents_returns_registered_names():
    service = _make_service()
    assert service.list_agents() == ["echo"]


def test_list_agents_raises_when_ai_disabled():
    service = _make_service(ai_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        service.list_agents()


def test_list_agents_raises_when_agents_capability_disabled():
    service = _make_service(agents_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        service.list_agents()


def test_run_returns_context_produced_by_the_sequence():
    service = _make_service()
    result = asyncio.run(service.run(["echo"], AgentContext(input="hi")))
    assert result.data["echoed"] == "hi"
    assert result.history == ["echo"]


def test_run_raises_when_agents_capability_disabled():
    service = _make_service(agents_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.run(["echo"], AgentContext(input="hi")))
