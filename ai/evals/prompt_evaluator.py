"""
AI Service Layer - Evals - Prompt Evaluation (Sprint 8)
OMS-360 Enterprise Food Delivery Platform

PromptEvaluator evaluates prompts by running them through an existing,
already-mock provider (ai/providers/mock_provider.py's MockAIProvider,
built in Sprint 4) via EvalRunner (Sprint 1). This deliberately reuses
the existing in-process mock completion path rather than adding a second
one - one source of truth for "what a mock AI call returns" across the
project. No real LLM is ever called; MockAIProvider.complete() never
performs network I/O (explicitly excluded from Sprint 8: Real LLM
Evaluation, External Evaluation Services, OpenAI Evals, LangSmith).
"""

from ai.evals.base import EvalReport
from ai.evals.runner import EvalRunner


class PromptEvaluator:
    def __init__(self, provider, runner: EvalRunner = None):
        self._provider = provider
        self._runner = runner or EvalRunner()

    async def evaluate(self, cases: list) -> EvalReport:
        async def _target(prompt):
            result = await self._provider.complete(prompt)
            return result["content"]

        return await self._runner.run(cases, _target)
