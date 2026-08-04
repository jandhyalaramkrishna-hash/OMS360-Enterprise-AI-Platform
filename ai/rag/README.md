# RAG Foundation — `ai/rag/`

**Status (Sprint 5, 2026-07-20+): the RAG package now has a full, real (mock) retrieval pipeline — `MockDocumentLoader` → `KnowledgeBase` → `SimpleDocumentParser` → `MockRetriever` → `ContextBuilder`, orchestrated by `RAGSearchService` — the first component in this project that runs retrieve-then-build-context end to end. `NotConfiguredRetriever` (Sprint 1) is unchanged and remains the fail-closed default when no retriever is wired up. No real vector database, embedding model, or external RAG framework was added.**

This file documents the RAG package specifically, per `docs/governance/DEVELOPMENT-STANDARDS.md` §8 ("module-level READMEs live beside the module they document"). See `ai/README.md` for the AI Service Layer as a whole.

## Purpose

Retrieval-Augmented Generation needs, at minimum, somewhere documents live, a way to turn them into retrievable pieces, a way to rank those pieces against a query, and a way to assemble the winners into a bounded block of context. This package is that pipeline — every stage sits behind its own abstract interface so a real backend (a document management system, a real chunker, a vector database) can replace any single stage later without touching the others. Sprint 5's explicit goal is the *architecture*, not a real AI service: every concrete implementation shipped this sprint is a mock, run entirely in-process.

## Components

| File | Sprint | Purpose |
|---|---|---|
| `base.py` | 1 | `RetrieverBase` — abstract interface: `async retrieve(query, top_k=5) -> list[RetrievedChunk]`. `RetrievedChunk` — frozen dataclass (`content`, `source`, `score`, `metadata`). |
| `retriever.py` | 1 | `NotConfiguredRetriever(RetrieverBase)` — fail-closed default; `retrieve()` always raises `AIProviderNotConfiguredError`. Unchanged this sprint. |
| `documents.py` | **5** | `KnowledgeBaseDocument` — the unit a document source produces and the Knowledge Base stores: `doc_id`, `title`, `content`, `source`, `metadata`. |
| `knowledge_base.py` | **5** | `KnowledgeBase` — in-memory store keyed by `doc_id`. Storage/lookup only: `add_document()`, `get_document()` (raises `AIKnowledgeBaseDocumentNotFoundError` if missing), `list_document_ids()`, `all_documents()`, `document_count()`, `clear()`. |
| `document_loader.py` | **5** | `DocumentLoaderBase` — abstract `load() -> list[KnowledgeBaseDocument]`. `MockDocumentLoader` — the only implementation this sprint; returns six fixed, built-in food-delivery FAQ documents (refund policy, order tracking, delivery windows, restaurant hours, payment issues, order cancellation). No filesystem/network access. |
| `document_parser.py` | **5** | `DocumentParserBase` — abstract `parse(document) -> list[ParsedChunk]`. `SimpleDocumentParser` — deterministic paragraph-first chunker with a character cap (`chunk_max_chars`, default 400), no NLP library. `ParsedChunk` — frozen dataclass (`chunk_id`, `document_id`, `content`, `source`, `chunk_index`, `metadata`). |
| `mock_retriever.py` | **5** | `MockRetriever(RetrieverBase)` — the **first retriever whose `retrieve()` actually runs**. Constructed with a pre-built `list[ParsedChunk]` (constructor injection — it does not depend on `KnowledgeBase`/`DocumentLoaderBase`/`DocumentParserBase` directly). Naive deterministic keyword-overlap scoring (`overlap / len(query_tokens)`, ties broken by `document_id`/`chunk_index` for stable ordering); chunks scoring 0 are excluded. An empty result is a normal outcome, not an error. |
| `context_builder.py` | **5** | `ContextBuilder.build_context(chunks, max_chars) -> BuiltContext`. Joins `[source] content` pieces up to a character budget; `BuiltContext.truncated` is `True` if any chunk was left out or the budget was hit. |
| `config.py` | **5** | `RAGConfig` / `load_rag_config()` — **tuning only** (`default_top_k`, `max_context_chars`, `chunk_max_chars`), read from `RAG_DEFAULT_TOP_K` / `RAG_MAX_CONTEXT_CHARS` / `RAG_CHUNK_MAX_CHARS`. Self-contained — does not import `ai/runtime/config.py` or `ai/config.py`. See "Configuration" below for why this is deliberately separate from enablement. |
| `search_service.py` | **5** | `RAGSearchService(retriever, context_builder, ai_service, rag_config)` — `async search(query, top_k=None) -> SearchResult`. The end-to-end orchestrator: validates the query, gates on `AIService.require_capability("rag_enabled")`, retrieves, builds context. |

## Configuration — tuning vs. enablement, deliberately separate

RAG has **two** independent configuration concerns, and Sprint 5 keeps them separate on purpose:

1. **Enablement** — is RAG allowed to run at all? This reuses the *existing* Sprint 2 mechanism unchanged: `RAG_ENABLED` + the master `AI_ENABLED` env vars, read by `ai.runtime.config.RuntimeConfiguration`, checked via `AIService.require_capability("rag_enabled")` — the same guard `ai/services/ai_service.py` already documented as intended for exactly this ("Future real RAG/MCP/Agents work should call this as a guard before running"). `RAGSearchService.search()` calls it on every request; nothing in `ai/runtime/`, `ai/config.py`, or `ai/services/ai_service.py` was modified this sprint.
2. **Tuning** — given that RAG is enabled, how many chunks to retrieve by default and how large a context/chunk may be. This is Sprint 5's new `ai/rag/config.py`: `RAG_DEFAULT_TOP_K` (default 5), `RAG_MAX_CONTEXT_CHARS` (default 2000), `RAG_CHUNK_MAX_CHARS` (default 400). These are never fail-closed gates — an unset or invalid value always falls back to its default, it never disables anything.

A minimal working configuration for local testing, requiring **no external credentials**:

```
AI_ENABLED=true
RAG_ENABLED=true
```

(`RAG_DEFAULT_TOP_K`, `RAG_MAX_CONTEXT_CHARS`, `RAG_CHUNK_MAX_CHARS` are optional — all three have working defaults.)

## The pipeline, end to end

`ai/dependencies.py` assembles the pipeline once, at module import time, as process-lifetime singletons — mirroring the Sprint 4 pattern for the provider framework:

1. `MockDocumentLoader().load()` → six `KnowledgeBaseDocument`
2. Each is added to a shared `KnowledgeBase`
3. `KnowledgeBase.all_documents()` (deterministic `doc_id` order) is parsed by `SimpleDocumentParser` into a flat `list[ParsedChunk]`
4. That list is passed into `MockRetriever(chunks)` via constructor injection
5. `RAGSearchService(retriever, context_builder, ai_service, rag_config)` composes the retriever, a `ContextBuilder`, the *existing* Sprint 2 `AIService` singleton (reused, not duplicated), and `RAGConfig`

`RAGSearchService.search(query, top_k=None)` is the one call that exercises all of this together — reachable via `ai.dependencies.get_search_service()`, not yet from any HTTP route (see below).

Errors are all `AIServiceError`-derived types with consistent JSON responses once wired into a route: `AIRagInvalidQueryError` (422, blank query), `AIFeatureDisabledError` (403, `AI_ENABLED` or `RAG_ENABLED` false), `AIKnowledgeBaseDocumentNotFoundError` (404, direct `KnowledgeBase.get_document()` lookup of an unknown `doc_id` — not raised by search itself, since an empty retrieval result is not an error).

## What Sprint 5 explicitly does NOT do

Per the Sprint 5 brief: no real vendor implementation, no real vector database (no ChromaDB, Pinecone, FAISS), no LangChain/LlamaIndex, no MCP, no AI Agents, no Kafka integration, no database integration, and no new FastAPI route was added to `app/main.py` or `app/api/ai/`. Every concrete implementation (`MockDocumentLoader`, `SimpleDocumentParser`, `MockRetriever`) is explicitly a mock — the goal is establishing the RAG architecture behind stable interfaces, not connecting to a real AI service. `RAGSearchService` is built, unit-tested, and reachable via `ai.dependencies.get_search_service()`, but nothing in `app/` calls it yet — wiring a search/query endpoint is a candidate for a future, separate, explicitly-approved sprint (see `docs/release/SPRINT-LOG.md`).

## Tests

`tests/ai/test_rag.py` (Sprint 1, `NotConfiguredRetriever` — unchanged, still passing), plus new Sprint 5 files: `tests/ai/test_knowledge_base.py`, `test_document_loader.py`, `test_document_parser.py`, `test_mock_retriever.py`, `test_context_builder.py`, `test_rag_config.py`, `test_search_service.py`, `test_dependencies_sprint5.py`. Same conventions as every other `ai/` test: plain `def test_...()` functions calling `asyncio.run(...)` rather than `async def`, so no `pytest-asyncio` dependency is needed; `monkeypatch` for anything environment-dependent.
