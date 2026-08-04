"""
AI Service Layer - RAG (Retrieval-Augmented Generation) primitives.

Sprint 1: RetrieverBase interface, RetrievedChunk, and the fail-closed
NotConfiguredRetriever default (base.py, retriever.py) - unchanged.

Sprint 5 (RAG Foundation) adds the pieces needed to actually run a mock
retrieval pipeline end to end, in-process, with no real vector store:

- documents.py       - KnowledgeBaseDocument (the unit the KB stores)
- knowledge_base.py  - KnowledgeBase (in-memory document store)
- document_loader.py - DocumentLoaderBase + MockDocumentLoader
- document_parser.py - DocumentParserBase + SimpleDocumentParser, ParsedChunk
- mock_retriever.py  - MockRetriever(RetrieverBase) - the first retriever
                        whose retrieve() actually runs
- context_builder.py - ContextBuilder + BuiltContext
- config.py          - RAGConfig / load_rag_config() (tuning only, not
                        enablement - see ai/rag/README.md)
- search_service.py  - RAGSearchService, the end-to-end orchestrator

See ai/rag/README.md for the full module documentation.
"""
