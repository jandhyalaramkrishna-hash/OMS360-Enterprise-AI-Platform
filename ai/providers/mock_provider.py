"""
AI Service Layer - Providers - Mock provider (Sprint 4)
OMS-360 Enterprise Food Delivery Platform

Unlike the four Sprint 2 adapters (OpenAI/Anthropic/Azure OpenAI/Ollama),
which are structurally real but deliberately never call out, MockAIProvider
is a fully in-process, deterministic provider whose complete() actually
returns a (simulated) result - no network call, no external SDK, no
credential required. It exists specifically so the rest of the Provider
Framework (ProviderFactory, AIChatService, ProviderHealthChecker,
configuration-based provider selection) has something safe to genuinely
call end-to-end this sprint.

This is NOT one of the excluded real providers (OpenAI/Claude/Gemini/Azure
OpenAI) - Sprint 4 explicitly forbids implementing any of those. Mock is a
distinct, permanent testing/demo provider, not a stand-in for a specific
real vendor.
"""

import asyncio

from app.core.logging_config import get_logger

from ai.core.exceptions import AIProviderCallFailedError
from ai.providers.base import BaseProvider

logger = get_logger("ai.providers.mock")

_MAX_ECHO_CHARS = 200


class MockAIProvider(BaseProvider):
    """Deterministic, in-process provider. Safe to call in any
    environment (tests, CI, local dev) - never reaches the network.

    Args:
        always_configured: if True (default), is_configured() always
            returns True (Mock needs no credentials by design). Set to
            False to exercise the "not configured" path in tests.
        simulate_failure: if True, complete() raises
            AIProviderCallFailedError instead of returning a result - lets
            callers (AIChatService, ProviderHealthChecker) be tested
            against a provider that is configured but fails at call time.
        simulated_latency_ms: optional artificial delay (via
            asyncio.sleep), useful for exercising latency-recording code
            paths (e.g. AIMetrics.record_provider_latency) deterministically.
    """

    name = "mock"
    required_env_vars = ()

    def __init__(
        self,
        always_configured: bool = True,
        simulate_failure: bool = False,
        simulated_latency_ms: float = 0.0,
    ):
        self._always_configured = always_configured
        self._simulate_failure = simulate_failure
        self._simulated_latency_ms = max(0.0, simulated_latency_ms)

    def is_configured(self) -> bool:
        return self._always_configured

    async def complete(self, prompt: str, **kwargs) -> dict:
        """Returns a deterministic, simulated completion. Never performs
        network I/O. Raises AIProviderCallFailedError if this instance was
        constructed with simulate_failure=True, so callers have a safe way
        to exercise their own error-handling paths."""
        if self._simulated_latency_ms:
            await asyncio.sleep(self._simulated_latency_ms / 1000)

        if self._simulate_failure:
            logger.warning("MockAIProvider.complete() simulating a failure (simulate_failure=True)")
            raise AIProviderCallFailedError(self.name, "MockAIProvider is configured to simulate a failure.")

        text = prompt.strip() if isinstance(prompt, str) else str(prompt)
        content = f"[mock] {text[:_MAX_ECHO_CHARS]}"
        usage = {
            "prompt_tokens": len(text.split()),
            "completion_tokens": len(content.split()),
            "total_tokens": len(text.split()) + len(content.split()),
        }
        logger.info("MockAIProvider.complete() called", extra={"ctx_prompt_length": len(text)})
        return {"content": content, "model": "mock-model-v1", "provider": self.name, "usage": usage}
