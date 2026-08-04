"""
Tests for ai/rag/document_loader.py — MockDocumentLoader returns a fixed,
deterministic set of built-in food-delivery FAQ documents, with no
filesystem/network access.
"""

from ai.rag.document_loader import MockDocumentLoader
from ai.rag.documents import KnowledgeBaseDocument


def test_load_returns_a_nonempty_list_of_knowledge_base_documents():
    documents = MockDocumentLoader().load()
    assert len(documents) >= 5
    assert all(isinstance(d, KnowledgeBaseDocument) for d in documents)


def test_load_documents_have_unique_doc_ids():
    documents = MockDocumentLoader().load()
    doc_ids = [d.doc_id for d in documents]
    assert len(doc_ids) == len(set(doc_ids))


def test_load_documents_have_nonblank_content_and_source():
    documents = MockDocumentLoader().load()
    for document in documents:
        assert document.content.strip()
        assert document.source.strip()
        assert document.title.strip()


def test_load_is_deterministic_across_calls():
    loader = MockDocumentLoader()
    first = loader.load()
    second = loader.load()
    assert [d.doc_id for d in first] == [d.doc_id for d in second]
    assert [d.content for d in first] == [d.content for d in second]


def test_load_covers_expected_faq_topics():
    documents = MockDocumentLoader().load()
    doc_ids = {d.doc_id for d in documents}
    assert "faq-refund-policy" in doc_ids
    assert "faq-order-tracking" in doc_ids
    assert "faq-delivery-windows" in doc_ids
