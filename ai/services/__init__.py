"""
AI Service Layer - Services
OMS-360 Enterprise Food Delivery Platform

Sprint 4 adds chat_service.py (AIChatService) - the first service that
actually calls a provider's complete() and returns a real result (always
via MockAIProvider this sprint) and exposes a live, per-provider health
check on top of ai.providers.health.ProviderHealthChecker.

Sprint 2: AIService (the top-level façade composing the Sprint 1
primitives with the Sprint 2 runtime configuration and provider
registry), ServiceRegistry (resolves named service instances),
ServiceFactory (builds fully-wired AIService/AIHealthService instances
consistently), and AIHealthService (verifies provider configuration,
runtime configuration, and feature flags - performs no network calls).
No concrete AI capability (chatbot, etc.) is built yet - the AI Customer
Support Chatbot documentation (DEC-0005) remains the most build-ready
candidate for a future, separate sprint.
"""
