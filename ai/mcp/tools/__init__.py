"""
AI Service Layer - MCP - Mock Tools (Sprint 6)

Four deterministic, in-process mock tools implementing ai.mcp.base.MCPTool:
OrderLookupTool, InventoryLookupTool, DeliveryStatusTool, KitchenStatusTool.
Each returns plausible, reproducible mock data derived only from its input
id - no database, no Kafka, no network call. See factory.py for
construction (MCPToolFactory) and ../README.md for the full module
documentation.
"""
