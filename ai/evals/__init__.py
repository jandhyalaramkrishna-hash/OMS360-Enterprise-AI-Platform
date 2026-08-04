"""
AI Service Layer - AI evaluation (evals) harness.

Sprint 1: EvalCase/EvalResult/EvalReport (base.py), EvalRunner
(runner.py) - unchanged in shape, still directly usable.

Sprint 8 additions: response_evaluator.py (comparator functions),
accuracy.py (AccuracyScorer), latency.py (LatencyAnalyzer - reads the
new EvalResult.execution_time_ms field runner.py now populates),
reports.py (EvaluationReportBuilder -> EvaluationSummary),
mock_dataset.py (MockEvalDataset), prompt_evaluator.py (PromptEvaluator,
reuses the existing Sprint 4 MockAIProvider), evaluation_service.py
(EvaluationService, capability-gated wrapper). See README.md for the
full pipeline and DEC-0021.
"""
