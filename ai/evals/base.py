"""
AI Service Layer - Evals - Data structures
OMS-360 Enterprise Food Delivery Platform
"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class EvalCase:
    """One evaluation case: an input, an expected output, and the
    comparison function used to score the actual output against it."""
    name: str
    input: Any
    expected: Any
    compare: Callable[[Any, Any], bool]


@dataclass
class EvalResult:
    case_name: str
    passed: bool
    actual: Any
    expected: Any
    error: str = None
    execution_time_ms: float = None  # Sprint 8 addition - populated by EvalRunner; see ai/evals/latency.py


@dataclass
class EvalReport:
    results: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        return (self.passed_count / self.total) if self.total else 0.0
