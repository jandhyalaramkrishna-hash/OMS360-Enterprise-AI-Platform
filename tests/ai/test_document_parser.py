"""
Tests for ai/rag/document_parser.py — SimpleDocumentParser is a
deterministic, paragraph-first chunker with a hard character cap. No NLP
library, no external dependency.
"""

import pytest

from ai.rag.document_parser import ParsedChunk, SimpleDocumentParser
from ai.rag.documents import KnowledgeBaseDocument


def _doc(content, doc_id="doc-1", source="unit-test"):
    return KnowledgeBaseDocument(doc_id=doc_id, title="Title", content=content, source=source, metadata={"k": "v"})


def test_short_document_becomes_a_single_chunk():
    parser = SimpleDocumentParser(chunk_max_chars=400)
    chunks = parser.parse(_doc("A short document."))
    assert len(chunks) == 1
    assert isinstance(chunks[0], ParsedChunk)
    assert chunks[0].content == "A short document."
    assert chunks[0].chunk_index == 0
    assert chunks[0].document_id == "doc-1"
    assert chunks[0].source == "unit-test"
    assert chunks[0].chunk_id == "doc-1::chunk-0"
    assert chunks[0].metadata == {"k": "v"}


def test_paragraphs_are_split_into_separate_chunks():
    parser = SimpleDocumentParser(chunk_max_chars=400)
    content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = parser.parse(_doc(content))
    assert len(chunks) == 3
    assert [c.content for c in chunks] == ["First paragraph.", "Second paragraph.", "Third paragraph."]
    assert [c.chunk_index for c in chunks] == [0, 1, 2]


def test_long_paragraph_is_split_on_char_boundary():
    parser = SimpleDocumentParser(chunk_max_chars=20)
    content = "one two three four five six seven eight nine ten"
    chunks = parser.parse(_doc(content))
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 20
    assert "".join(c.content for c in chunks).replace(" ", "") == content.replace(" ", "")


def test_blank_lines_and_whitespace_only_paragraphs_are_dropped():
    parser = SimpleDocumentParser(chunk_max_chars=400)
    content = "First.\n\n\n\n   \n\nSecond."
    chunks = parser.parse(_doc(content))
    assert [c.content for c in chunks] == ["First.", "Second."]


def test_empty_document_content_produces_no_chunks():
    parser = SimpleDocumentParser(chunk_max_chars=400)
    chunks = parser.parse(_doc("   "))
    assert chunks == []


def test_chunk_max_chars_must_be_positive():
    with pytest.raises(ValueError):
        SimpleDocumentParser(chunk_max_chars=0)
    with pytest.raises(ValueError):
        SimpleDocumentParser(chunk_max_chars=-5)


def test_parse_is_deterministic_across_calls():
    parser = SimpleDocumentParser(chunk_max_chars=50)
    document = _doc("First paragraph here.\n\nSecond paragraph that is a bit longer than the first one.")
    first = parser.parse(document)
    second = parser.parse(document)
    assert [c.content for c in first] == [c.content for c in second]
