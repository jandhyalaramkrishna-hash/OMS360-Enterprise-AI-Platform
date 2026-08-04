"""
AI Service Layer - Providers - Base provider interface
OMS-360 Enterprise Food Delivery Platform

Sprint 2 scope: providers are PREPARED (structurally real, correctly
report their own configuration state) but never CALLED - no provider's
complete() may perform a network request or SDK call this sprint. See
each concrete provider module for the specific rationale.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Contract every AI provider adapter must implement."""

    name: str
    required_env_vars: tuple = ()

    @abstractmethod
    def is_configured(self) -> bool:
        """True if this provider has everything it needs to be called
        (e.g. an API key/endpoint). Does NOT mean it has been verified
        reachable - that would require an actual network call, out of
        scope for Sprint 2."""
        raise NotImplementedError

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> dict:
        """Perform a completion/generation call. No Sprint 2 provider
        implements a real call yet - each one raises a clear,
        fail-closed error instead."""
        raise NotImplementedError
