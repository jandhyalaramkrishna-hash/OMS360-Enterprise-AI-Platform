"""
AI Service Layer - MCP (Model Context Protocol) tool-calling primitives.

Sprint 1: MCPTool interface and MCPToolRegistry (base.py, registry.py) -
unchanged.

Sprint 6 (MCP Foundation) adds an in-process server framework around them
and four deterministic mock tools - no real MCP client, transport, or
external service:

- models.py   - MCPRequest / MCPResponse / ToolDescriptor / ToolCallResult
- router.py   - MCPRequestRouter (method dispatch + request validation)
- server.py   - MCPServer (capability-gated list_tools()/call_tool())
- health.py   - MCPHealthChecker / ToolHealthResult
- config.py   - MCPConfig / load_mcp_config() (tuning only, not enablement
                - see ai/mcp/README.md)
- tools/      - OrderLookupTool, InventoryLookupTool, DeliveryStatusTool,
                KitchenStatusTool, and MCPToolFactory

See ai/mcp/README.md for the full module documentation.
"""
