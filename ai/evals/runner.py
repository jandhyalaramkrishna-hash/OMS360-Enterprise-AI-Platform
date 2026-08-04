"""
AI Service Layer - Evals - Runner
OMS-360 Enterprise Food Delivery Platform

Runs a list of EvalCase objects against any async callable and produces a
structured EvalReport. Deliberately generic - this can evaluate a
prompt/model call once one exists, or any other async function in the
meantime (e.g. a retriever or tool), so it's real, usable infrastructure
today rather than code that only becomes useful once an LLM is wired up.

Sprint 8 change: the per-case elapsed time (already measured via Timer)
is now also stored on EvalResult.execution_time_ms, not just logged - so
ai/evals/latency.py's LatencyAnalyzer has real per-case data to
aggregate. Purely additive; existing callers that only read
report.total/passed_count/pass_rate are unaffected.
"""

from app.core.logging_config import get_logger, Timer

from ai.evals.base import EvalReport, EvalResult

logger = get_logger("ai.evals")


class EvalRunner:
    async def run(self, cases: list, target) -> EvalReport:
        report = EvalReport()
        logger.info("Eval run started", extra={"ctx_case_count": len(cases)})
        for case in cases:
            with Timer() as t:
                try:
                    actual = await target(case.input)
                    passed = bool(case.compare(actual, case.expected))
                    result = EvalResult(case_name=case.name, passed=passed, actual=actual, expected=case.expected)
                except Exception as exc:  # noqa: BLE001 - one bad eval case must not crash the whole run
                    result = EvalResult(
                        case_name=case.name, passed=False, actual=None,
                        expected=case.expected, error=str(exc),
                    )
            result.execution_time_ms = round(t.elapsed_ms, 2)
            logger.info(
                "Eval case complete",
                extra={
                    "ctx_case_name": case.name,
                    "ctx_passed": result.passed,
                    "ctx_execution_time_ms": round(t.elapsed_ms, 2),
                },
            )
            report.results.append(result)
        logger.info(
            "Eval run complete",
            extra={"ctx_total": report.total, "ctx_passed": report.passed_count, "ctx_pass_rate": report.pass_rate},
        )
        return report
