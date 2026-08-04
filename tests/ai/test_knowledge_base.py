"""
Tests for ai/rag/knowledge_base.py — KnowledgeBase is storage/lookup only:
add, get (raising AIKnowledgeBaseDocumentNotFoundError when missing),
list, iterate in deterministic order, count, clear.
"""

import pytest

from ai.core.exceptions import AIKnowledgeBaseDocumentNotFoundError
from ai.rag.documents import KnowledgeBaseDocument
from ai.rag.knowledge_base import KnowledgeBase


def _doc(doc_id, content="some content", title="Title", source="unit-test"):
    return KnowledgeBaseDocument(doc_id=doc_id, title=title, content=content, source=source)


def test_new_knowledge_base_is_empty():
    kb = KnowledgeBase()
    assert kb.document_count() == 0
    assert kb.list_document_ids() == []
    assert kb.all_documents() == []


def test_add_document_then_get_document_round_trips():
    kb = KnowledgeBase()
    doc = _doc("doc-1")
    kb.add_document(doc)
    assert kb.get_document("doc-1") is doc
    assert kb.document_count() == 1


def test_get_document_raises_for_unknown_doc_id():
    kb = KnowledgeBase()
    with pytest.raises(AIKnowledgeBaseDocumentNotFoundError):
        kb.get_document("does-not-exist")


def test_get_document_error_carries_doc_id():
    kb = KnowledgeBase()
    try:
        kb.get_document("missing-doc")
    except AIKnowledgeBaseDocumentNotFoundError as exc:
        assert exc.doc_id == "missing-doc"
        assert exc.status_code == 404
    else:
        pytest.fail("expected AIKnowledgeBaseDocumentNotFoundError")


def test_add_document_with_duplicate_doc_id_overwrites():
    kb = KnowledgeBase()
    kb.add_document(_doc("doc-1", content="first"))
    kb.add_document(_doc("doc-1", content="second"))
    assert kb.document_count() == 1
    assert kb.get_document("doc-1").content == "second"


def test_all_documents_ordered_deterministically_by_doc_id():
    kb = KnowledgeBase()
    kb.add_document(_doc("zebra"))
    kb.add_document(_doc("alpha"))
    kb.add_document(_doc("mid"))
    assert [d.doc_id for d in kb.all_documents()] == ["alpha", "mid", "zebra"]
    assert kb.list_document_ids() == ["alpha", "mid", "zebra"]


def test_clear_empties_the_knowledge_base():
    kb = KnowledgeBase()
    kb.add_document(_doc("doc-1"))
    kb.clear()
    assert kb.document_count() == 0
    assert kb.list_document_ids() == []
