"""
AI Service Layer - MCP - Request/Response models (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

Plain, dependency-free dataclasses describing the shape of an in-process
MCP request/response and the two payload types MCPRequestRouter produces.
These deliberately mirror the request/response *shape* of the real Model
Context Protocol (a JSON-RPC-style "method" + "params" envelope, a tool
descriptor for listing, a tool-call result) without implementing any real
MCP client, transport, or wire format - this sprint's scope is the
architecture, exercised entirely in-process.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolDescriptor:
    """What MCPRequestRouter returns for a "tools/list" request - one
    entry per tool registered in the MCPToolRegistry it was built with."""

    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCallResult:
    """What MCPRequestRouter returns for a successful "tools/call"
    request. `output` is whatever JSON-serializable dict the tool's
    execute() returned, unmodified."""

    tool_name: str
    output: dict
    is_mock: bool = True


@dataclass(frozen=True)
class MCPRequest:
    """A single in-process MCP-style request. `method` is currently one of
    "tools/list" or "tools/call" - see MCPRequestRouter for the supported
    set. `params` is method-specific: empty for "tools/list", and
    {"name": <tool name>, "arguments": {...}} for "tools/call"."""

    method: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MCPResponse:
    """The outcome of routing one MCPRequest. Exactly one of `result`/
    `error` is meaningful depending on `success` - callers that only need
    the happy path can rely on MCPRequestRouter.route() raising instead
    (see MCPRequestRouter), this envelope exists for parity with the real
    protocol's response shape."""

    success: bool
    result: object = None
    error: str = None
