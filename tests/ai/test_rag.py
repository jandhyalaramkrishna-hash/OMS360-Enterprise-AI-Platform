"""
Tests for ai/rag — NotConfiguredRetriever must fail closed, not fabricate
or silently return empty results.
"""

import asyncio

import pytest

from ai.core.exceptions import AIProviderNotConfiguredError
from ai.rag.retriever import NotConfiguredRetriever


def test_not_configured_retriever_raises():
    retriever = NotConfiguredRetriever()
    with pytest.raises(AIProviderNotConfiguredError):
        asyncio.run(retriever.retrieve("what is the refund policy?"))


def test_not_configured_retriever_raises_regardless_of_top_k():
    retriever = NotConfiguredRetriever()
    with pytest.raises(AIProviderNotConfiguredError):
        asyncio.run(retriever.retrieve("query", top_k=1))
