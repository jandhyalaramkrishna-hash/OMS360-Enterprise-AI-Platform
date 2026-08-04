"""
AI Service Layer - MCP - Configuration (Sprint 6)
OMS-360 Enterprise Food Delivery Platform

MCPConfig holds only MCP-specific *tuning* parameters - it deliberately
does NOT duplicate or replace the existing enablement/feature-flag
machinery. Whether MCP is enabled at all is decided exclusively by
ai.runtime.config.RuntimeConfiguration.is_capability_enabled("mcp_enabled")
via AIService.require_capability(), the same pattern established for RAG
in Sprint 5 (see ai/rag/config.py, DEC-0018). This module is self-contained
(no import of ai/runtime/config.py or ai/config.py) so MCP tuning can be
changed without touching the enablement system, and vice versa.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # idempotent - see ai/runtime/config.py for the same pattern

_DEFAULT_TOOL_CALL_TIMEOUT_MS = 5000


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class MCPConfig:
    """An immutable snapshot of Sprint 6's MCP tuning parameters. Build
    via load_mcp_config(), not directly."""

    tool_call_timeout_ms: int


def load_mcp_config() -> MCPConfig:
    """Reads MCP_TOOL_CALL_TIMEOUT_MS from the environment, falling back
    to a 5000ms default when unset or invalid. Like ai/rag/config.py, this
    is a tuning parameter, not a fail-closed gate - a missing/invalid value
    here never disables MCP, it only leaves the timeout at its default.
    MCPRequestRouter enforces this timeout around every tool.execute()
    call, so even today's in-process mock tools are bounded the same way a
    future real (I/O-bound) tool implementation would need to be."""
    return MCPConfig(
        tool_call_timeout_ms=_env_int("MCP_TOOL_CALL_TIMEOUT_MS", _DEFAULT_TOOL_CALL_TIMEOUT_MS),
    )
