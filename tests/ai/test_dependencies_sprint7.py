"""
Tests for the Sprint 7 additions to ai/dependencies.py — the assembled
multi-agent pipeline singletons (message bus, health checker, service)
and that the six mock agents were registered into the SAME shared
orchestrator Sprint 1 already built, not a second one.
"""

from ai.agents.agent_service import AgentService
from ai.agents.factory import AgentFactory
from ai.agents.health import AgentHealthChecker
from ai.agents.messaging import AgentMessageBus
from ai.dependencies import (
    get_agent_health_checker,
    get_agent_message_bus,
    get_agent_orchestrator,
    get_agent_service,
    get_ai_service,
)


def test_sprint7_providers_return_singletons():
    assert get_agent_message_bus() is get_agent_message_bus()
    assert get_agent_health_checker() is get_agent_health_checker()
    assert get_agent_service() is get_agent_service()


def test_get_agent_message_bus_returns_message_bus_instance():
    assert isinstance(get_agent_message_bus(), AgentMessageBus)


def test_get_agent_health_checker_returns_health_checker_instance():
    assert isinstance(get_agent_health_checker(), AgentHealthChecker)


def test_get_agent_service_returns_agent_service_instance():
    assert isinstance(get_agent_service(), AgentService)


def test_agent_service_shares_the_same_ai_service_singleton():
    assert get_agent_service()._ai_service is get_ai_service()


def test_agent_service_shares_the_same_orchestrator_singleton():
    assert get_agent_service()._orchestrator is get_agent_orchestrator()


def test_orchestrator_contains_all_six_known_mock_agents():
    assert set(get_agent_orchestrator().list_agents()) == set(
        AgentFactory(AgentMessageBus()).known_agent_names()
    )
