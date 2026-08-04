"""
AI Service Layer - Providers - Provider registry
OMS-360 Enterprise Food Delivery Platform
"""

from app.core.logging_config import get_logger

from ai.core.exceptions import AIProviderNotFoundError
from ai.providers.base import BaseProvider

logger = get_logger("ai.providers")


class ProviderRegistry:
    def __init__(self):
        self._providers = {}
        logger.info("ProviderRegistry initialized", extra={"ctx_provider_count": 0})

    def register(self, provider: BaseProvider) -> None:
        if provider.name in self._providers:
            logger.warning("Overwriting already-registered provider", extra={"ctx_provider_name": provider.name})
        self._providers[provider.name] = provider
        logger.info(
            "Provider registered",
            extra={"ctx_provider_name": provider.name, "ctx_configured": provider.is_configured()},
        )

    def get_provider(self, name: str) -> BaseProvider:
        if name not in self._providers:
            raise AIProviderNotFoundError(name)
        return self._providers[name]

    def list_providers(self) -> list:
        return sorted(self._providers.keys())

    def list_configured_providers(self) -> list:
        return sorted(name for name, p in self._providers.items() if p.is_configured())
