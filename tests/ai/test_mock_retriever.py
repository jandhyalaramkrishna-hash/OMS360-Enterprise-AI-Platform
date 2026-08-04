"""
Tests for ai/rag/mock_retriever.py — MockRetriever, the first
RetrieverBase implementation whose retrieve() actually runs: deterministic
keyword-overlap scoring over a pre-built, constructor-injected list of
ParsedChunk. No embeddings, no external service.
"""

import asyncio

from ai.rag.base import RetrievedChunk
from ai.rag.document_parser import ParsedChunk
from ai.rag.mock_retriever import MockRetriever


def _chunk(chunk_id, content, document_id="doc-1", chunk_index=0, source="unit-test"):
    return ParsedChunk(
        chunk_id=chunk_id, document_id=document_id, content=content, source=source, chunk_index=chunk_index
    )


def test_retrieve_returns_matching_chunks_scored_and_ordered():
    chunks = [
        _chunk("c1", "The refund policy allows returns within 48 hours.", document_id="refunds"),
        _chunk("c2", "Delivery windows depend on restaurant preparation time.", document_id="delivery"),
    ]
    retriever = MockRetriever(chunks)
    results = asyncio.run(retriever.retrieve("what is the refund policy", top_k=5))
    assert len(results) == 1
    assert isinstance(results[0], RetrievedChunk)
    assert results[0].source == "unit-test"
    assert results[0].metadata["document_id"] == "refunds"
    assert results[0].metadata["chunk_id"] == "c1"
    assert 0 < results[0].score <= 1.0


def test_retrieve_returns_empty_list_when_nothing_matches():
    chunks = [_chunk("c1", "Completely unrelated content about kitchens.")]
    retriever = MockRetriever(chunks)
    results = asyncio.run(retriever.retrieve("spacecraft telemetry data", top_k=5))
    assert results == []


def test_retrieve_returns_empty_list_when_no_chunks_configured():
    retriever = MockRetriever([])
    results = asyncio.run(retriever.retrieve("refund policy", top_k=5))
    assert results == []


def test_retrieve_returns_empty_list_for_blank_query():
    chunks = [_chunk("c1", "refund policy content")]
    retriever = MockRetriever(chunks)
    results = asyncio.run(retriever.retrieve("   ", top_k=5))
    assert results == []


def test_retrieve_respects_top_k():
    chunks = [
        _chunk("c1", "refund refund refund policy"),
        _chunk("c2", "refund policy details"),
        _chunk("c3", "refund policy summary"),
    ]
    retriever = MockRetriever(chunks)
    results = asyncio.run(retriever.retrieve("refund policy", top_k=2))
    assert len(results) == 2


def test_retrieve_orders_higher_overlap_score_first():
    chunks = [
        _chunk("c1", "refund", document_id="a"),
        _chunk("c2", "refund policy details in full", document_id="b"),
    ]
    retriever = MockRetriever(chunks)
    results = asyncio.run(retriever.retrieve("refund policy", top_k=5))
    assert len(results) == 2
    assert results[0].score >= results[1].score


def test_retrieve_is_deterministic_across_calls():
    chunks = [
        _chunk("c1", "refund policy alpha", document_id="a"),
        _chunk("c2", "refund policy beta", document_id="b"),
    ]
    retriever = MockRetriever(chunks)
    first = asyncio.run(retriever.retrieve("refund policy", top_k=5))
    second = asyncio.run(retriever.retrieve("refund policy", top_k=5))
    assert [r.metadata["chunk_id"] for r in first] == [r.metadata["chunk_id"] for r in second]
