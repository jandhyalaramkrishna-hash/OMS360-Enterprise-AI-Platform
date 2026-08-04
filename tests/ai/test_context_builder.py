"""
Tests for ai/rag/context_builder.py — ContextBuilder assembles
RetrievedChunk objects into one bounded text block and reports whether
anything was left out to respect the character budget.
"""

import pytest

from ai.rag.base import RetrievedChunk
from ai.rag.context_builder import BuiltContext, ContextBuilder


def _chunk(content, source="src", score=1.0):
    return RetrievedChunk(content=content, source=source, score=score, metadata={})


def test_build_context_with_no_chunks_is_empty_and_not_truncated():
    result = ContextBuilder().build_context([], max_chars=1000)
    assert isinstance(result, BuiltContext)
    assert result.text == ""
    assert result.chunk_count == 0
    assert result.truncated is False
    assert result.total_chars == 0


def test_build_context_includes_source_marker_and_content():
    result = ContextBuilder().build_context([_chunk("hello world", source="faq-1")], max_chars=1000)
    assert result.text == "[faq-1] hello world"
    assert result.chunk_count == 1
    assert result.truncated is False


def test_build_context_joins_multiple_chunks_with_blank_line():
    chunks = [_chunk("first", source="a"), _chunk("second", source="b")]
    result = ContextBuilder().build_context(chunks, max_chars=1000)
    assert result.text == "[a] first\n\n[b] second"
    assert result.chunk_count == 2


def test_build_context_truncates_when_budget_exceeded():
    chunks = [_chunk("x" * 50, source="a"), _chunk("y" * 50, source="b")]
    result = ContextBuilder().build_context(chunks, max_chars=60)
    assert result.chunk_count == 1
    assert result.truncated is True
    assert "y" * 50 not in result.text


def test_build_context_not_truncated_when_everything_fits_exactly():
    chunks = [_chunk("short", source="a")]
    result = ContextBuilder().build_context(chunks, max_chars=len("[a] short"))
    assert result.truncated is False
    assert result.chunk_count == 1


def test_max_chars_must_be_positive():
    with pytest.raises(ValueError):
        ContextBuilder().build_context([], max_chars=0)
    with pytest.raises(ValueError):
        ContextBuilder().build_context([], max_chars=-1)
