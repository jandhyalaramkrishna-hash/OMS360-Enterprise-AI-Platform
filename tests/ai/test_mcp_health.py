"""
Tests for ai/mcp/health.py — MCPHealthChecker: a live probe that actually
calls each tool's execute(), building probe arguments generically from
the tool's own input_schema.
"""

import asyncio

from ai.mcp.base import MCPTool
from ai.mcp.health import MCPHealthChecker, ToolHealthResult
from ai.mcp.tools.factory import MCPToolFactory


class _AlwaysFailsTool(MCPTool):
    name = "always_fails"
    description = "Always raises, for health-check failure testing."
    input_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs) -> dict:
        raise RuntimeError("simulated failure")


def test_check_reports_healthy_for_a_working_tool():
    checker = MCPHealthChecker()
    result = asyncio.run(checker.check(MCPToolFactory.create_all()[0]))
    assert isinstance(result, ToolHealthResult)
    assert result.healthy is True
    assert result.error is None


def test_check_builds_probe_arguments_from_required_schema_fields():
    checker = MCPHealthChecker()
    for tool in MCPToolFactory.create_all():
        result = asyncio.run(checker.check(tool))
        assert result.tool_name == tool.name
        assert result.healthy is True


def test_check_reports_unhealthy_when_tool_raises():
    checker = MCPHealthChecker()
    result = asyncio.run(checker.check(_AlwaysFailsTool()))
    assert result.healthy is False
    assert "simulated failure" in result.error


def test_check_all_covers_every_tool():
    checker = MCPHealthChecker()
    tools = MCPToolFactory.create_all()
    results = asyncio.run(checker.check_all(tools))
    assert {r.tool_name for r in results} == {t.name for t in tools}
    assert all(r.healthy for r in results)
