"""
Tests for ai/mcp/server.py — MCPServer: capability-gated list_tools()/
call_tool(), delegating to MCPRequestRouter.
"""

import asyncio

import pytest

from ai.core.exceptions import AIFeatureDisabledError, AIMCPInvalidRequestError
from ai.mcp.base import MCPTool
from ai.mcp.config import MCPConfig
from ai.mcp.models import ToolCallResult, ToolDescriptor
from ai.mcp.registry import MCPToolRegistry
from ai.mcp.router import MCPRequestRouter
from ai.mcp.server import MCPServer
from ai.providers.mock_provider import MockAIProvider
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.ai_service import AIService


class _EchoTool(MCPTool):
    name = "echo"
    description = "Echoes back its input."
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    async def execute(self, **kwargs) -> dict:
        return {"echoed": kwargs.get("text")}


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    if "mcp_enabled" in overrides:
        base["feature_flags"] = {**base["feature_flags"], "mcp_enabled": overrides["mcp_enabled"]}
    return RuntimeConfiguration(**base)


def _ai_service(ai_enabled=True, mcp_enabled=True):
    registry = ProviderRegistry()
    registry.register(MockAIProvider())
    return AIService(_runtime_config(ai_enabled=ai_enabled, mcp_enabled=mcp_enabled), ValidationResult(), registry)


def _make_server(ai_enabled=True, mcp_enabled=True, timeout_ms=5000):
    registry = MCPToolRegistry()
    registry.register(_EchoTool())
    router = MCPRequestRouter(registry, MCPConfig(tool_call_timeout_ms=timeout_ms))
    return MCPServer(router, _ai_service(ai_enabled=ai_enabled, mcp_enabled=mcp_enabled))


def test_list_tools_returns_descriptors():
    server = _make_server()
    tools = asyncio.run(server.list_tools())
    assert len(tools) == 1
    assert isinstance(tools[0], ToolDescriptor)
    assert tools[0].name == "echo"


def test_list_tools_raises_when_ai_disabled():
    server = _make_server(ai_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(server.list_tools())


def test_list_tools_raises_when_mcp_capability_disabled():
    server = _make_server(mcp_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(server.list_tools())


def test_call_tool_returns_tool_call_result():
    server = _make_server()
    result = asyncio.run(server.call_tool("echo", {"text": "hello"}))
    assert isinstance(result, ToolCallResult)
    assert result.tool_name == "echo"
    assert result.output == {"echoed": "hello"}


def test_call_tool_defaults_arguments_to_empty_dict():
    server = _make_server()
    with pytest.raises(AIMCPInvalidRequestError):
        asyncio.run(server.call_tool("echo"))


def test_call_tool_raises_when_mcp_capability_disabled():
    server = _make_server(mcp_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(server.call_tool("echo", {"text": "hi"}))
