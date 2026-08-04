"""
AI Service Layer - MCP - Tool registry
OMS-360 Enterprise Food Delivery Platform

A plain, dependency-injectable registry. No tools are registered by
default - concrete tools (and the decision of what OMS360 data/actions
they're allowed to touch) are a separate, later decision. Registering a
tool here does not expose it anywhere; it only makes it resolvable by
name for whatever calls this registry.
"""

from app.core.logging_config import get_logger

from ai.core.exceptions import AIToolNotFoundError
from ai.mcp.base import MCPTool

logger = get_logger("ai.mcp")


class MCPToolRegistry:
    def __init__(self):
        self._tools = {}
        logger.info("MCPToolRegistry initialized", extra={"ctx_tool_count": 0})

    def register(self, tool: MCPTool) -> None:
        if tool.name in self._tools:
            logger.warning("Overwriting already-registered MCP tool", extra={"ctx_tool_name": tool.name})
        self._tools[tool.name] = tool
        logger.info("MCP tool registered", extra={"ctx_tool_name": tool.name})

    def get_tool(self, name: str) -> MCPTool:
        if name not in self._tools:
            raise AIToolNotFoundError(name)
        return self._tools[name]

    def list_tools(self) -> list:
        return sorted(self._tools.keys())
