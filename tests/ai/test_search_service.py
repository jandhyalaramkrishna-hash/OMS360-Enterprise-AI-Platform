"""
Tests for ai/rag/search_service.py — RAGSearchService, the end-to-end RAG
orchestrator: validates the query, gates on the existing
AIService.require_capability("rag_enabled"), retrieves, builds context.
"""

import asyncio

import pytest

from ai.core.exceptions import AIFeatureDisabledError, AIRagInvalidQueryError
from ai.providers.mock_provider import MockAIProvider
from ai.providers.registry import ProviderRegistry
from ai.rag.config import RAGConfig
from ai.rag.context_builder import ContextBuilder
from ai.rag.document_parser import ParsedChunk
from ai.rag.mock_retriever import MockRetriever
from ai.rag.search_service import RAGSearchService, SearchResult
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.ai_service import AIService


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    if "rag_enabled" in overrides:
        base["feature_flags"] = {**base["feature_flags"], "rag_enabled": overrides["rag_enabled"]}
    return RuntimeConfiguration(**base)


def _ai_service(ai_enabled=True, rag_enabled=True):
    registry = ProviderRegistry()
    registry.register(MockAIProvider())
    return AIService(_runtime_config(ai_enabled=ai_enabled, rag_enabled=rag_enabled), ValidationResult(), registry)


def _chunk(chunk_id, content, document_id="doc-1", chunk_index=0):
    return ParsedChunk(chunk_id=chunk_id, document_id=document_id, content=content, source="src", chunk_index=chunk_index)


def _make_service(chunks=None, ai_enabled=True, rag_enabled=True, rag_config=None):
    chunks = chunks if chunks is not None else [_chunk("c1", "refund policy details")]
    retriever = MockRetriever(chunks)
    return RAGSearchService(
        retriever,
        ContextBuilder(),
        _ai_service(ai_enabled=ai_enabled, rag_enabled=rag_enabled),
        rag_config or RAGConfig(default_top_k=5, max_context_chars=2000, chunk_max_chars=400),
    )


def test_search_returns_matching_chunks_and_context():
    service = _make_service()
    result = asyncio.run(service.search("refund policy"))
    assert isinstance(result, SearchResult)
    assert result.query == "refund policy"
    assert len(result.chunks) == 1
    assert result.context.chunk_count == 1
    assert "refund policy details" in result.context.text


def test_search_returns_empty_result_when_nothing_matches():
    service = _make_service(chunks=[_chunk("c1", "totally unrelated kitchen content")])
    result = asyncio.run(service.search("spacecraft telemetry"))
    assert result.chunks == []
    assert result.context.chunk_count == 0
    assert result.context.text == ""


def test_search_rejects_blank_query():
    service = _make_service()
    with pytest.raises(AIRagInvalidQueryError):
        asyncio.run(service.search("   "))


def test_search_rejects_blank_query_even_when_rag_disabled():
    service = _make_service(rag_enabled=False)
    with pytest.raises(AIRagInvalidQueryError):
        asyncio.run(service.search(""))


def test_search_raises_when_ai_disabled():
    service = _make_service(ai_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.search("refund policy"))


def test_search_raises_when_rag_capability_disabled():
    service = _make_service(rag_enabled=False)
    with pytest.raises(AIFeatureDisabledError):
        asyncio.run(service.search("refund policy"))


def test_search_uses_default_top_k_when_not_specified():
    chunks = [_chunk(f"c{i}", "refund policy match", chunk_index=i) for i in range(10)]
    service = _make_service(chunks=chunks, rag_config=RAGConfig(default_top_k=3, max_context_chars=2000, chunk_max_chars=400))
    result = asyncio.run(service.search("refund policy"))
    assert len(result.chunks) == 3


def test_search_explicit_top_k_overrides_default():
    chunks = [_chunk(f"c{i}", "refund policy match", chunk_index=i) for i in range(10)]
    service = _make_service(chunks=chunks, rag_config=RAGConfig(default_top_k=3, max_context_chars=2000, chunk_max_chars=400))
    result = asyncio.run(service.search("refund policy", top_k=1))
    assert len(result.chunks) == 1
