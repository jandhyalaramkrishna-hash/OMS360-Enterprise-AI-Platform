"""
AI Service Layer - MCP - Server Framework (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

MCPServer is the ergonomic entry point over MCPRequestRouter, mirroring
the role AIChatService (Sprint 4) and RAGSearchService (Sprint 5) play for
their respective subsystems: it is the one place that (a) gates on
AIService.require_capability("mcp_enabled") and (b) offers a plain
async-method API (list_tools()/call_tool()) instead of requiring every
caller to build an MCPRequest envelope by hand. The envelope/dispatch
machinery itself lives in MCPRequestRouter, kept separate so the protocol
shape (method/params/response) can be exercised directly (e.g. by a future
real MCP transport) without depending on this convenience layer.
"""

from typing import Optional

from app.core.logging_config import get_logger

from ai.mcp.models import MCPRequest, ToolCallResult
from ai.mcp.router import MCPRequestRouter
from ai.services.ai_service import AIService

logger = get_logger("ai.mcp.server")


class MCPServer:
    """Constructed via the shared ai.dependencies.get_mcp_server()
    singleton - not directly."""

    def __init__(self, router: MCPRequestRouter, ai_service: AIService):
        self._router = router
        self._ai_service = ai_service
        logger.info("MCPServer initialized")

    async def list_tools(self) -> list:
        """Returns every registered tool as a ToolDescriptor. Raises
        AIFeatureDisabledError unless AI_ENABLED and MCP_ENABLED are both
        true."""
        self._ai_service.require_capability("mcp_enabled")
        response = await self._router.route(MCPRequest(method="tools/list"))
        return response.result["tools"]

    async def call_tool(self, name: str, arguments: Optional[dict] = None) -> ToolCallResult:
        """Calls one registered tool by name. Raises
        AIFeatureDisabledError (MCP disabled), AIMCPInvalidRequestError
        (blank name or a required argument missing), AIToolNotFoundError
        (unregistered name), AIMCPToolCallTimeoutError, or
        AIMCPToolExecutionError (the tool raised during execute())."""
        self._ai_service.require_capability("mcp_enabled")
        response = await self._router.route(
            MCPRequest(method="tools/call", params={"name": name, "arguments": arguments or {}})
        )
        return response.result
