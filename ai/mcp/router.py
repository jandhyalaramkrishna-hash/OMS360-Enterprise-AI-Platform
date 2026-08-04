"""
AI Service Layer - MCP - Request Router (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

MCPRequestRouter dispatches an in-process MCPRequest to the right
handler by `method`, mirroring the method-dispatch shape of the real
Model Context Protocol (a JSON-RPC-style "tools/list" / "tools/call"
envelope) without implementing any real MCP client or wire transport -
everything here is a plain Python function call. Single Responsibility:
protocol-level dispatch and request-shape validation (unknown method,
missing tool name, missing required argument) - it does not decide
whether MCP is enabled (that's AIService.require_capability, called by
MCPServer before a request ever reaches this router) and it does not
implement any tool's domain logic (that's each MCPTool).
"""

import asyncio

from app.core.logging_config import get_logger

from ai.core.exceptions import (
    AIMCPInvalidRequestError,
    AIMCPToolCallTimeoutError,
    AIMCPToolExecutionError,
    AIMCPUnsupportedMethodError,
    AIServiceError,
)
from ai.mcp.config import MCPConfig
from ai.mcp.models import MCPRequest, MCPResponse, ToolCallResult, ToolDescriptor
from ai.mcp.registry import MCPToolRegistry

logger = get_logger("ai.mcp.router")

SUPPORTED_METHODS = ("tools/list", "tools/call")


class MCPRequestRouter:
    """Constructed with the shared MCPToolRegistry (see
    ai.dependencies.get_tool_registry()) and an MCPConfig for the
    per-call timeout. Not constructed with an AIService - enablement is
    MCPServer's concern, not the router's."""

    def __init__(self, tool_registry: MCPToolRegistry, mcp_config: MCPConfig):
        self._tool_registry = tool_registry
        self._mcp_config = mcp_config
        logger.info("MCPRequestRouter initialized")

    async def route(self, request: MCPRequest) -> MCPResponse:
        if request.method == "tools/list":
            return self._handle_list()
        if request.method == "tools/call":
            return await self._handle_call(request.params or {})
        raise AIMCPUnsupportedMethodError(request.method, SUPPORTED_METHODS)

    def _handle_list(self) -> MCPResponse:
        descriptors = [
            ToolDescriptor(name=name, description=tool.description, input_schema=dict(tool.input_schema))
            for name, tool in self._iter_tools()
        ]
        logger.info("MCP tools/list handled", extra={"ctx_tool_count": len(descriptors)})
        return MCPResponse(success=True, result={"tools": descriptors})

    async def _handle_call(self, params: dict) -> MCPResponse:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise AIMCPInvalidRequestError("A tools/call request must include a non-empty string 'name'.")

        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise AIMCPInvalidRequestError("A tools/call request's 'arguments' must be an object.")

        tool = self._tool_registry.get_tool(name)  # raises AIToolNotFoundError if unregistered
        self._validate_arguments(tool, arguments)

        timeout_seconds = self._mcp_config.tool_call_timeout_ms / 1000
        try:
            output = await asyncio.wait_for(tool.execute(**arguments), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("MCP tool call timed out", extra={"ctx_tool_name": name})
            raise AIMCPToolCallTimeoutError(name, self._mcp_config.tool_call_timeout_ms)
        except AIServiceError:
            raise
        except Exception as exc:
            logger.warning("MCP tool call failed", extra={"ctx_tool_name": name, "ctx_error": str(exc)})
            raise AIMCPToolExecutionError(name, str(exc))

        logger.info("MCP tools/call handled", extra={"ctx_tool_name": name})
        return MCPResponse(success=True, result=ToolCallResult(tool_name=name, output=output))

    def _validate_arguments(self, tool, arguments: dict) -> None:
        required = tool.input_schema.get("required", []) if tool.input_schema else []
        missing = [field for field in required if arguments.get(field) in (None, "")]
        if missing:
            raise AIMCPInvalidRequestError(
                f"Missing required argument(s) for tool '{tool.name}': {', '.join(missing)}."
            )

    def _iter_tools(self):
        for name in self._tool_registry.list_tools():
            yield name, self._tool_registry.get_tool(name)
