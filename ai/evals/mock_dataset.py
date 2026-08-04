"""
AI Service Layer - Evals - Mock Evaluation Dataset (Sprint 8)
OMS-360 Enterprise Food Delivery Platform

MockEvalDataset is a small, built-in set of EvalCases usable immediately
for exercising PromptEvaluator/EvalRunner without any real LLM - mirrors
MockDocumentLoader's six built-in FAQ documents (Sprint 5) and
MCPToolFactory's four built-in mock tools (Sprint 6): built-in,
deterministic, mock data ready to use out of the box. Each case's
`expected` is a keyword that must appear in the (mock) response, paired
with the `contains_keyword` comparator - since PromptEvaluator's target
(ai.providers.mock_provider.MockAIProvider) always echoes the prompt back
with a "[mock] " prefix, the input keyword itself is always present in a
successful response, and cases are trivially reusable to exercise a
failure path by pointing at a keyword that will never appear.
"""

from ai.evals.base import EvalCase
from ai.evals.response_evaluator import contains_keyword


class MockEvalDataset:
    def cases(self) -> list:
        return [
            EvalCase(name="refund_policy_keyword", input="refund policy", expected="refund", compare=contains_keyword),
            EvalCase(name="order_tracking_keyword", input="track my order", expected="track", compare=contains_keyword),
            EvalCase(name="delivery_window_keyword", input="delivery window", expected="delivery", compare=contains_keyword),
            EvalCase(name="cancel_order_keyword", input="cancel my order", expected="cancel", compare=contains_keyword),
            EvalCase(name="payment_issue_keyword", input="payment issue", expected="payment", compare=contains_keyword),
            EvalCase(name="restaurant_hours_keyword", input="restaurant hours", expected="hours", compare=contains_keyword),
        ]
