"""
AI Service Layer - MCP - Health Check (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

MCPHealthChecker is a live-but-safe probe, mirroring
ai.providers.health.ProviderHealthChecker's role for the provider
framework (Sprint 4): it actually calls each tool's execute() rather than
only inspecting configuration. Safe for every tool in this package, since
every Sprint 6 tool is a deterministic, in-process mock with no network/
credential/database dependency - a future real (I/O-bound) tool would need
to tolerate being probed the same way.

The checker does not need per-tool knowledge of which argument names mean
what: it builds probe arguments generically from each tool's own
input_schema (every field listed as "required" gets a fixed placeholder
value), the same "ask the interface, not the implementation" approach
input validation uses in ai/mcp/router.py.
"""

from dataclasses import dataclass
from typing import Optional

from app.core.logging_config import get_logger

from ai.mcp.base import MCPTool

logger = get_logger("ai.mcp.health")

_PROBE_VALUE = "healthcheck-probe"


@dataclass(frozen=True)
class ToolHealthResult:
    tool_name: str
    healthy: bool
    error: Optional[str] = None


class MCPHealthChecker:
    async def check(self, tool: MCPTool) -> ToolHealthResult:
        arguments = self._build_probe_arguments(tool)
        try:
            await tool.execute(**arguments)
        except Exception as exc:
            logger.warning("MCP tool health check failed", extra={"ctx_tool_name": tool.name})
            return ToolHealthResult(tool_name=tool.name, healthy=False, error=str(exc))
        return ToolHealthResult(tool_name=tool.name, healthy=True)

    async def check_all(self, tools: list) -> list:
        return [await self.check(tool) for tool in tools]

    def _build_probe_arguments(self, tool: MCPTool) -> dict:
        required = tool.input_schema.get("required", []) if tool.input_schema else []
        return {field: _PROBE_VALUE for field in required}
