"""
Tests for ai/rag/config.py — RAGConfig / load_rag_config() are tuning-only
parameters with working defaults; unset or invalid env vars never disable
anything (fail-open on tuning, distinct from the fail-closed enablement
flags in ai/runtime/config.py).
"""

from ai.rag.config import RAGConfig, load_rag_config


def test_load_rag_config_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("RAG_DEFAULT_TOP_K", raising=False)
    monkeypatch.delenv("RAG_MAX_CONTEXT_CHARS", raising=False)
    monkeypatch.delenv("RAG_CHUNK_MAX_CHARS", raising=False)
    config = load_rag_config()
    assert isinstance(config, RAGConfig)
    assert config.default_top_k == 5
    assert config.max_context_chars == 2000
    assert config.chunk_max_chars == 400


def test_load_rag_config_reads_env_vars(monkeypatch):
    monkeypatch.setenv("RAG_DEFAULT_TOP_K", "3")
    monkeypatch.setenv("RAG_MAX_CONTEXT_CHARS", "500")
    monkeypatch.setenv("RAG_CHUNK_MAX_CHARS", "100")
    config = load_rag_config()
    assert config.default_top_k == 3
    assert config.max_context_chars == 500
    assert config.chunk_max_chars == 100


def test_load_rag_config_falls_back_to_default_on_invalid_value(monkeypatch):
    monkeypatch.setenv("RAG_DEFAULT_TOP_K", "not-a-number")
    config = load_rag_config()
    assert config.default_top_k == 5


def test_load_rag_config_falls_back_to_default_on_non_positive_value(monkeypatch):
    monkeypatch.setenv("RAG_MAX_CONTEXT_CHARS", "0")
    config = load_rag_config()
    assert config.max_context_chars == 2000

    monkeypatch.setenv("RAG_MAX_CONTEXT_CHARS", "-100")
    config = load_rag_config()
    assert config.max_context_chars == 2000


def test_load_rag_config_falls_back_to_default_on_blank_value(monkeypatch):
    monkeypatch.setenv("RAG_CHUNK_MAX_CHARS", "   ")
    config = load_rag_config()
    assert config.chunk_max_chars == 400
