"""
Tests for the Sprint 5 additions to ai/dependencies.py — the assembled RAG
pipeline singletons (knowledge base, document loader/parser, retriever,
context builder, rag config, search service) and that MockRetriever was
constructed from real, parsed, loaded documents.
"""

from ai.dependencies import (
    get_ai_service,
    get_context_builder,
    get_document_loader,
    get_document_parser,
    get_knowledge_base,
    get_rag_config,
    get_retriever,
    get_search_service,
)
from ai.rag.config import RAGConfig
from ai.rag.context_builder import ContextBuilder
from ai.rag.document_loader import MockDocumentLoader
from ai.rag.document_parser import SimpleDocumentParser
from ai.rag.knowledge_base import KnowledgeBase
from ai.rag.mock_retriever import MockRetriever
from ai.rag.search_service import RAGSearchService


def test_sprint5_providers_return_singletons():
    assert get_knowledge_base() is get_knowledge_base()
    assert get_document_loader() is get_document_loader()
    assert get_document_parser() is get_document_parser()
    assert get_retriever() is get_retriever()
    assert get_context_builder() is get_context_builder()
    assert get_rag_config() is get_rag_config()
    assert get_search_service() is get_search_service()


def test_get_knowledge_base_returns_populated_instance():
    kb = get_knowledge_base()
    assert isinstance(kb, KnowledgeBase)
    assert kb.document_count() > 0


def test_get_document_loader_returns_mock_document_loader_instance():
    assert isinstance(get_document_loader(), MockDocumentLoader)


def test_get_document_parser_returns_simple_document_parser_instance():
    assert isinstance(get_document_parser(), SimpleDocumentParser)


def test_get_retriever_returns_mock_retriever_instance():
    assert isinstance(get_retriever(), MockRetriever)


def test_get_context_builder_returns_context_builder_instance():
    assert isinstance(get_context_builder(), ContextBuilder)


def test_get_rag_config_returns_rag_config_instance():
    assert isinstance(get_rag_config(), RAGConfig)


def test_get_search_service_returns_search_service_instance():
    assert isinstance(get_search_service(), RAGSearchService)


def test_search_service_shares_the_same_retriever_and_context_builder():
    service = get_search_service()
    assert service._retriever is get_retriever()
    assert service._context_builder is get_context_builder()


def test_search_service_shares_the_same_ai_service_singleton():
    assert get_search_service()._ai_service is get_ai_service()


def test_knowledge_base_document_count_matches_mock_document_loader_output():
    assert get_knowledge_base().document_count() == len(MockDocumentLoader().load())
