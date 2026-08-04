"""
Tests for ai/mcp/config.py — MCPConfig / load_mcp_config() is a
tuning-only parameter with a working default; an unset or invalid env var
never disables anything (fail-open on tuning, same split RAGConfig uses).
"""

from ai.mcp.config import MCPConfig, load_mcp_config


def test_load_mcp_config_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("MCP_TOOL_CALL_TIMEOUT_MS", raising=False)
    config = load_mcp_config()
    assert isinstance(config, MCPConfig)
    assert config.tool_call_timeout_ms == 5000


def test_load_mcp_config_reads_env_var(monkeypatch):
    monkeypatch.setenv("MCP_TOOL_CALL_TIMEOUT_MS", "1500")
    config = load_mcp_config()
    assert config.tool_call_timeout_ms == 1500


def test_load_mcp_config_falls_back_to_default_on_invalid_value(monkeypatch):
    monkeypatch.setenv("MCP_TOOL_CALL_TIMEOUT_MS", "not-a-number")
    config = load_mcp_config()
    assert config.tool_call_timeout_ms == 5000


def test_load_mcp_config_falls_back_to_default_on_non_positive_value(monkeypatch):
    monkeypatch.setenv("MCP_TOOL_CALL_TIMEOUT_MS", "0")
    config = load_mcp_config()
    assert config.tool_call_timeout_ms == 5000

    monkeypatch.setenv("MCP_TOOL_CALL_TIMEOUT_MS", "-100")
    config = load_mcp_config()
    assert config.tool_call_timeout_ms == 5000


def test_load_mcp_config_falls_back_to_default_on_blank_value(monkeypatch):
    monkeypatch.setenv("MCP_TOOL_CALL_TIMEOUT_MS", "   ")
    config = load_mcp_config()
    assert config.tool_call_timeout_ms == 5000
