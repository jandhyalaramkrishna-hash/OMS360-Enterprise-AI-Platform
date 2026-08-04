"""
Tests for the Sprint 9 additions to ai/dependencies.py — the assembled
integration singletons, and that both are built from the SAME Sprint
2-8 singletons already wired earlier in the module, not second instances
of anything.
"""

from ai.dependencies import (
    get_agent_health_checker,
    get_agent_orchestrator,
    get_agent_service,
    get_ai_health_service,
    get_ai_metrics,
    get_ai_service,
    get_ai_workflow_service,
    get_chat_service,
    get_evaluation_service,
    get_mcp_health_checker,
    get_mcp_server,
    get_mock_eval_dataset,
    get_platform_health_checker,
    get_provider_health_checker,
    get_provider_registry,
    get_search_service,
    get_tool_registry,
)
from ai.integration.health import PlatformHealthChecker
from ai.integration.workflow_service import AIWorkflowService


def test_sprint9_providers_return_singletons():
    assert get_platform_health_checker() is get_platform_health_checker()
    assert get_ai_workflow_service() is get_ai_workflow_service()


def test_get_platform_health_checker_returns_instance():
    assert isinstance(get_platform_health_checker(), PlatformHealthChecker)


def test_get_ai_workflow_service_returns_instance():
    assert isinstance(get_ai_workflow_service(), AIWorkflowService)


def test_platform_health_checker_shares_the_same_ai_health_service_singleton():
    assert get_platform_health_checker()._ai_health_service is get_ai_health_service()


def test_platform_health_checker_shares_the_same_provider_collaborators():
    assert get_platform_health_checker()._provider_health_checker is get_provider_health_checker()
    assert get_platform_health_checker()._provider_registry is get_provider_registry()


def test_platform_health_checker_shares_the_same_mcp_collaborators():
    assert get_platform_health_checker()._mcp_health_checker is get_mcp_health_checker()
    assert get_platform_health_checker()._tool_registry is get_tool_registry()


def test_platform_health_checker_shares_the_same_agent_collaborators():
    assert get_platform_health_checker()._agent_health_checker is get_agent_health_checker()
    assert get_platform_health_checker()._agent_orchestrator is get_agent_orchestrator()


def test_platform_health_checker_shares_the_same_ai_metrics_singleton():
    assert get_platform_health_checker()._ai_metrics is get_ai_metrics()


def test_workflow_service_shares_the_same_ai_service_singleton():
    assert get_ai_workflow_service()._ai_service is get_ai_service()


def test_workflow_service_shares_the_same_search_service_singleton():
    assert get_ai_workflow_service()._search_service is get_search_service()


def test_workflow_service_shares_the_same_mcp_server_singleton():
    assert get_ai_workflow_service()._mcp_server is get_mcp_server()


def test_workflow_service_shares_the_same_agent_service_singleton():
    assert get_ai_workflow_service()._agent_service is get_agent_service()


def test_workflow_service_shares_the_same_chat_service_singleton():
    assert get_ai_workflow_service()._chat_service is get_chat_service()


def test_workflow_service_shares_the_same_evaluation_service_singleton():
    assert get_ai_workflow_service()._evaluation_service is get_evaluation_service()


def test_workflow_service_shares_the_same_mock_eval_dataset_singleton():
    assert get_ai_workflow_service()._mock_eval_dataset is get_mock_eval_dataset()
