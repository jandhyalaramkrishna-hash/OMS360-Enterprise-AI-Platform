"""
Tests for ai/mcp/router.py — MCPRequestRouter: method dispatch,
protocol-level request validation, per-call timeout enforcement, and
wrapping of unexpected tool-execution failures.
"""

import asyncio

import pytest

from ai.core.exceptions import (
    AIMCPInvalidRequestError,
    AIMCPToolCallTimeoutError,
    AIMCPToolExecutionError,
    AIMCPUnsupportedMethodError,
    AIToolNotFoundError,
)
from ai.mcp.base import MCPTool
from ai.mcp.config import MCPConfig
from ai.mcp.models import MCPRequest, MCPResponse, ToolCallResult, ToolDescriptor
from ai.mcp.registry import MCPToolRegistry
from ai.mcp.router import MCPRequestRouter


class _EchoTool(MCPTool):
    name = "echo"
    description = "Echoes back its input."
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    async def execute(self, **kwargs) -> dict:
        return {"echoed": kwargs.get("text")}


class _FailingTool(MCPTool):
    name = "boom"
    description = "Always raises."
    input_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs) -> dict:
        raise RuntimeError("kaboom")


class _SlowTool(MCPTool):
    name = "slow"
    description = "Sleeps longer than the configured timeout."
    input_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs) -> dict:
        await asyncio.sleep(0.2)
        return {"done": True}


def _router(*tools, timeout_ms=5000):
    registry = MCPToolRegistry()
    for tool in tools:
        registry.register(tool)
    return MCPRequestRouter(registry, MCPConfig(tool_call_timeout_ms=timeout_ms))


def test_tools_list_returns_descriptors_for_every_registered_tool():
    router = _router(_EchoTool())
    response = asyncio.run(router.route(MCPRequest(method="tools/list")))
    assert isinstance(response, MCPResponse)
    assert response.success is True
    tools = response.result["tools"]
    assert len(tools) == 1
    assert isinstance(tools[0], ToolDescriptor)
    assert tools[0].name == "echo"
    assert tools[0].input_schema["required"] == ["text"]


def test_tools_call_happy_path_returns_tool_call_result():
    router = _router(_EchoTool())
    response = asyncio.run(
        router.route(MCPRequest(method="tools/call", params={"name": "echo", "arguments": {"text": "hi"}}))
    )
    assert response.success is True
    assert isinstance(response.result, ToolCallResult)
    assert response.result.tool_name == "echo"
    assert response.result.output == {"echoed": "hi"}
    assert response.result.is_mock is True


def test_unsupported_method_raises():
    router = _router(_EchoTool())
    with pytest.raises(AIMCPUnsupportedMethodError):
        asyncio.run(router.route(MCPRequest(method="tools/delete")))


def test_tools_call_with_blank_name_raises_invalid_request():
    router = _router(_EchoTool())
    with pytest.raises(AIMCPInvalidRequestError):
        asyncio.run(router.route(MCPRequest(method="tools/call", params={"name": "", "arguments": {}})))


def test_tools_call_with_missing_name_raises_invalid_request():
    router = _router(_EchoTool())
    with pytest.raises(AIMCPInvalidRequestError):
        asyncio.run(router.route(MCPRequest(method="tools/call", params={})))


def test_tools_call_with_non_dict_arguments_raises_invalid_request():
    router = _router(_EchoTool())
    with pytest.raises(AIMCPInvalidRequestError):
        asyncio.run(router.route(MCPRequest(method="tools/call", params={"name": "echo", "arguments": "nope"})))


def test_tools_call_unknown_tool_raises_tool_not_found():
    router = _router(_EchoTool())
    with pytest.raises(AIToolNotFoundError):
        asyncio.run(router.route(MCPRequest(method="tools/call", params={"name": "does_not_exist"})))


def test_tools_call_missing_required_argument_raises_invalid_request():
    router = _router(_EchoTool())
    with pytest.raises(AIMCPInvalidRequestError):
        asyncio.run(router.route(MCPRequest(method="tools/call", params={"name": "echo", "arguments": {}})))


def test_tools_call_wraps_unexpected_tool_exception():
    router = _router(_FailingTool())
    with pytest.raises(AIMCPToolExecutionError):
        asyncio.run(router.route(MCPRequest(method="tools/call", params={"name": "boom"})))


def test_tools_call_enforces_timeout():
    router = _router(_SlowTool(), timeout_ms=10)
    with pytest.raises(AIMCPToolCallTimeoutError):
        asyncio.run(router.route(MCPRequest(method="tools/call", params={"name": "slow"})))
