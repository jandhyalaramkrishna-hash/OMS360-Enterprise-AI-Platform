"""
Tests for ai/mcp — MCPToolRegistry register/get/list behavior.
"""

import asyncio

import pytest

from ai.core.exceptions import AIToolNotFoundError
from ai.mcp.base import MCPTool
from ai.mcp.registry import MCPToolRegistry


class _EchoTool(MCPTool):
    name = "echo"
    description = "Echoes back its input."
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}

    async def execute(self, **kwargs) -> dict:
        return {"echoed": kwargs.get("text")}


def test_registry_starts_empty():
    registry = MCPToolRegistry()
    assert registry.list_tools() == []


def test_register_and_get_tool():
    registry = MCPToolRegistry()
    registry.register(_EchoTool())
    assert registry.list_tools() == ["echo"]
    tool = registry.get_tool("echo")
    result = asyncio.run(tool.execute(text="hello"))
    assert result == {"echoed": "hello"}


def test_get_unregistered_tool_raises():
    registry = MCPToolRegistry()
    with pytest.raises(AIToolNotFoundError):
        registry.get_tool("does_not_exist")


def test_registering_same_name_twice_overwrites():
    registry = MCPToolRegistry()
    registry.register(_EchoTool())
    registry.register(_EchoTool())
    assert registry.list_tools() == ["echo"]
