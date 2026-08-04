"""
AI Service Layer - Providers
OMS-360 Enterprise Food Delivery Platform

Sprint 2: base provider interface (base.py), provider registry
(registry.py), and four prepared-but-not-called provider adapters -
OpenAI, Anthropic, Azure OpenAI, and Ollama. "Prepared" means each
provider correctly reports whether it's configured (via environment
variables) but its complete() method deliberately raises rather than
making any network/API call - no provider is actually called in Sprint 2.
No LLM SDK dependency has been added to requirements.txt, since none of
them are used yet. Wiring a real call to a real vendor (OpenAI, Claude,
Gemini, Azure OpenAI) remains out of scope and is a future,
explicitly-scoped sprint.

Sprint 4 adds: mock_provider.py (MockAIProvider - the first provider whose
complete() actually returns a result, entirely in-process, no network call
or credential), factory.py (ProviderFactory - owns provider construction
by name, used by ai.services.factory.ServiceFactory), and health.py
(ProviderHealthChecker - a live-but-safe call-through health probe,
distinct from ai.services.health_service.AIHealthService's
configuration-only check).
"""
