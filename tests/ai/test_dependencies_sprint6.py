"""
Tests for the Sprint 6 additions to ai/dependencies.py — the assembled MCP
pipeline singletons (config, router, server, health checker) and that the
four mock tools were registered into the SAME shared tool registry Sprint
1 already built, not a second one.
"""

from ai.dependencies import (
    get_ai_service,
    get_mcp_config,
    get_mcp_health_checker,
    get_mcp_router,
    get_mcp_server,
    get_tool_registry,
)
from ai.mcp.config import MCPConfig
from ai.mcp.health import MCPHealthChecker
from ai.mcp.router import MCPRequestRouter
from ai.mcp.server import MCPServer
from ai.mcp.tools.factory import MCPToolFactory


def test_sprint6_providers_return_singletons():
    assert get_mcp_config() is get_mcp_config()
    assert get_mcp_router() is get_mcp_router()
    assert get_mcp_server() is get_mcp_server()
    assert get_mcp_health_checker() is get_mcp_health_checker()


def test_get_mcp_config_returns_mcp_config_instance():
    assert isinstance(get_mcp_config(), MCPConfig)


def test_get_mcp_router_returns_mcp_request_router_instance():
    assert isinstance(get_mcp_router(), MCPRequestRouter)


def test_get_mcp_server_returns_mcp_server_instance():
    assert isinstance(get_mcp_server(), MCPServer)


def test_get_mcp_health_checker_returns_mcp_health_checker_instance():
    assert isinstance(get_mcp_health_checker(), MCPHealthChecker)


def test_mcp_server_shares_the_same_ai_service_singleton():
    assert get_mcp_server()._ai_service is get_ai_service()


def test_mcp_server_shares_the_same_router_singleton():
    assert get_mcp_server()._router is get_mcp_router()


def test_tool_registry_contains_all_four_known_mock_tools():
    assert set(get_tool_registry().list_tools()) == set(MCPToolFactory.known_tool_names())


def test_mcp_router_uses_the_same_shared_tool_registry():
    assert get_mcp_router()._tool_registry is get_tool_registry()
