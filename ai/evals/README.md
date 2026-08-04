# AI Evaluation Framework — `ai/evals/`

**Status (Sprint 8, 2026-07-20 IST+): the evals package now has a full, real (mock) evaluation pipeline — `MockEvalDataset` → `PromptEvaluator` (reuses the Sprint 4 `MockAIProvider`) → `EvalRunner` (Sprint 1, reused, now records per-case latency) → `EvaluationReportBuilder` (`AccuracyScorer` + `LatencyAnalyzer`) → `EvaluationService` — the first component in this project that scores accuracy and latency for a batch of mock prompt evaluations end to end. No real LLM evaluation, external evaluation service, or human review workflow was added.**

This file documents the evals package specifically, per `docs/governance/DEVELOPMENT-STANDARDS.md` §8 ("module-level READMEs live beside the module they document"). See `ai/README.md` for the AI Service Layer as a whole.

## Purpose

An evaluation framework answers two questions about a batch of AI calls: how many were correct, and how fast were they? This package builds that shape entirely in-process: a runnable dataset of cases, a way to run them against a target (any async callable — a prompt call, a retriever, a tool), and a report combining accuracy and latency. Sprint 8's explicit goal is the *architecture*, not a real evaluation service — the one target exercised this sprint is `MockAIProvider` (Sprint 4's in-process, deterministic mock), and every dataset shipped is built-in mock data.

## Components

| File | Sprint | Purpose |
|---|---|---|
| `base.py` | 1 / **8** | `EvalCase` (name, input, expected, compare), `EvalReport` (total/passed_count/pass_rate) — unchanged. `EvalResult` gains `execution_time_ms` (Sprint 8, default `None`), populated by `EvalRunner`. |
| `runner.py` | 1 / **8** | `EvalRunner.run(cases, target) -> EvalReport` — unchanged in shape; Sprint 8 now stores the already-measured per-case `Timer` elapsed time onto `EvalResult.execution_time_ms`, not just the structured log line. |
| `response_evaluator.py` | **8** | `exact_match`, `contains_keyword`, `contains_all_keywords` — plain comparator functions usable as an `EvalCase.compare` callable. |
| `accuracy.py` | **8** | `AccuracyScorer.score(report) -> AccuracyScore` (total/passed/failed/accuracy) — a dedicated home for a future, more nuanced accuracy definition, kept separate from `EvalReport.pass_rate` itself. |
| `latency.py` | **8** | `LatencyAnalyzer.analyze(report) -> LatencyMetrics` (min/max/avg/total ms, sample count) — aggregates `EvalResult.execution_time_ms` across a report. |
| `reports.py` | **8** | `EvaluationReportBuilder.build(report) -> EvaluationSummary` — combines `AccuracyScorer` + `LatencyAnalyzer` + the raw per-case results into one consolidated structure. |
| `mock_dataset.py` | **8** | `MockEvalDataset.cases()` — six built-in `EvalCase`s (refund policy, order tracking, delivery window, cancel order, payment issue, restaurant hours), paired with `contains_keyword`. |
| `prompt_evaluator.py` | **8** | `PromptEvaluator.evaluate(cases) -> EvalReport` — runs cases through an injected provider's `complete()` (the *existing* `MockAIProvider`, reused) via `EvalRunner`. |
| `evaluation_service.py` | **8** | `EvaluationService(runner, report_builder, ai_service)` — the ergonomic, policy-enforcing entry point: `async evaluate(cases, target) -> EvaluationSummary`, gated on `AIService.require_capability("evals_enabled")`. |

## The pipeline, end to end

`ai/dependencies.py` assembles the pipeline once, at module import time, as process-lifetime singletons — the same pattern used for Sprint 6's MCP pipeline and Sprint 7's agent pipeline:

1. `PromptEvaluator` is constructed over the **same** `_provider_registry`'s `"mock"` provider Sprint 2/4 already built (not a second `MockAIProvider` instance)
2. `EvaluationReportBuilder(AccuracyScorer(), LatencyAnalyzer())` is constructed
3. `EvaluationService(runner, report_builder, ai_service)` composes the **same** `_eval_runner` singleton Sprint 1 already built and the **same** Sprint 2 `AIService` singleton (reused, not duplicated)

`EvaluationService.evaluate(cases, target)` is the call that exercises all of this together — reachable via `ai.dependencies.get_evaluation_service()`, not yet from any HTTP route (see below). A typical run using the built-in dataset and the shared mock provider:

```python
dataset = get_mock_eval_dataset()
evaluator = get_prompt_evaluator()
report = await evaluator.evaluate(dataset.cases())
summary = get_evaluation_report_builder().build(report)
# summary.accuracy.accuracy, summary.latency.avg_ms, summary.case_results
```

Errors are all `AIServiceError`-derived types with consistent JSON responses once wired into a route: `AIFeatureDisabledError` (403, `AI_ENABLED` or `EVALS_ENABLED` false). `EvalRunner` itself never raises for a failing case — a target's exception is captured as `EvalResult.error` so one bad case cannot crash a whole run (Sprint 1 behavior, unchanged).

## Design decisions (DEC-0021)

- **One shared mock provider, not a second one.** `PromptEvaluator` is built over the *existing* `_provider_registry.get_provider("mock")` singleton Sprint 2/4 already built and exposed via `ai.dependencies.get_provider_registry()`, the same "reuse the existing shared collaborator" choice DEC-0017/0018/0019/0020 made for their respective registries.
- **Accuracy and latency are separate, composable scorers, not fields bolted onto `EvalReport`.** `EvalReport` (Sprint 1) stays a raw pass/fail list; `AccuracyScorer` and `LatencyAnalyzer` are independent, single-purpose classes that both read from it, and `EvaluationReportBuilder` is the one place that combines them — adding a third dimension later (e.g. a cost scorer) means one more scorer class, not a change to `EvalReport`'s shape.
- **`EvalResult.execution_time_ms` is additive, not a new result type.** `EvalRunner` already measured this via `Timer` and only logged it (Sprint 1); Sprint 8 stores the same already-computed value on the result object so `LatencyAnalyzer` has real data, without introducing a parallel "timed eval result" type.
- **Runner vs. Service split.** `EvalRunner` owns pure execution mechanics (run cases against a target, capture pass/fail/timing) and has no knowledge of enablement — mirroring `MCPRequestRouter`/`AgentOrchestrator`'s role from Sprint 6/7. `EvaluationService` owns the *policy* concern (capability gating) and hands off to `EvaluationReportBuilder` for the consolidated summary.

## What Sprint 8 explicitly does NOT do

Per the Sprint 8 brief: no real LLM evaluation, no external evaluation service, no OpenAI Evals, no LangSmith, and no human review workflow. `PromptEvaluator`'s only exercised target is `MockAIProvider.complete()` — fully in-process, deterministic, no network call. `EvaluationService` is built, unit-tested, and reachable via `ai.dependencies.get_evaluation_service()`, but nothing in `app/` calls it yet — wiring an evaluation-run endpoint is a candidate for a future, separate, explicitly-approved sprint (see `docs/release/SPRINT-LOG.md`).

## Tests

`tests/ai/test_evals.py` (Sprint 1, `EvalRunner` — unchanged, still passing), plus new Sprint 8 files: `tests/ai/test_response_evaluator.py`, `test_accuracy.py`, `test_latency.py`, `test_eval_reports.py`, `test_mock_eval_dataset.py`, `test_prompt_evaluator.py`, `test_evaluation_service.py`, `test_dependencies_sprint8.py`. Same conventions as every other `ai/` test: plain `def test_...()` functions calling `asyncio.run(...)` rather than `async def`, so no `pytest-asyncio` dependency is needed.
