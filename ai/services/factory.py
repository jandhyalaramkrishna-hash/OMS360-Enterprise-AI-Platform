"""
AI Service Layer - Services - Service factory
OMS-360 Enterprise Food Delivery Platform

Builds fully-wired AIService/AIHealthService/AIChatService instances from
the runtime configuration loader and a populated ProviderRegistry, so
callers never construct these by hand and every instance is built
consistently.

Sprint 4: provider *construction* (which classes exist, how to instantiate
one by name) moved out of this file and into ai.providers.factory.
ProviderFactory - ServiceFactory now delegates to it rather than holding
its own hardcoded provider-class tuple, keeping this file focused on
composing services, not building providers.
"""

from app.core.logging_config import get_logger

from ai.metrics import get_ai_metrics
from ai.providers.factory import ProviderFactory
from ai.providers.health import ProviderHealthChecker
from ai.providers.registry import ProviderRegistry
from ai.runtime.loader import get_runtime_config_loader
from ai.services.ai_service import AIService
from ai.services.chat_service import AIChatService
from ai.services.health_service import AIHealthService

logger = get_logger("ai.services.factory")


class ServiceFactory:
    @staticmethod
    def build_provider_registry() -> ProviderRegistry:
        return ProviderFactory.build_registry()

    @staticmethod
    def build_ai_service() -> AIService:
        loader = get_runtime_config_loader()
        runtime_config = loader.load()
        validation = loader.validation()
        provider_registry = ServiceFactory.build_provider_registry()
        logger.info("AIService built via ServiceFactory")
        return AIService(runtime_config, validation, provider_registry)

    @staticmethod
    def build_health_service() -> AIHealthService:
        loader = get_runtime_config_loader()
        runtime_config = loader.load()
        validation = loader.validation()
        provider_registry = ServiceFactory.build_provider_registry()
        logger.info("AIHealthService built via ServiceFactory")
        return AIHealthService(runtime_config, validation, provider_registry)

    @staticmethod
    def build_chat_service() -> AIChatService:
        """Sprint 4: builds a fully-wired AIChatService - its own
        AIService (for the master AI_ENABLED gate + configuration-based
        provider selection), its own ProviderRegistry (built the same way
        as build_ai_service()/build_health_service() above, so "mock" and
        every other known provider are always registered), a fresh
        ProviderHealthChecker (stateless, cheap to construct), and the
        existing process-lifetime AIMetrics singleton (Sprint 2) so chat
        activity feeds the same counters GET /api/v1/ai/metrics already
        reports."""
        loader = get_runtime_config_loader()
        runtime_config = loader.load()
        validation = loader.validation()
        provider_registry = ServiceFactory.build_provider_registry()
        ai_service = AIService(runtime_config, validation, provider_registry)
        health_checker = ProviderHealthChecker()
        logger.info("AIChatService built via ServiceFactory")
        return AIChatService(ai_service, provider_registry, health_checker, get_ai_metrics())
