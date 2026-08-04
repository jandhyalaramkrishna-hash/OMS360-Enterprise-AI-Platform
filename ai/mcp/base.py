"""
AI Service Layer - MCP - Tool interface
OMS-360 Enterprise Food Delivery Platform
"""

from abc import ABC, abstractmethod


class MCPTool(ABC):
    """Contract every MCP-style tool must implement. `input_schema` is a
    JSON Schema dict describing the tool's expected arguments, matching
    the shape MCP clients expect when listing available tools."""

    name: str
    description: str
    input_schema: dict

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """Run the tool and return a JSON-serializable result."""
        raise NotImplementedError
