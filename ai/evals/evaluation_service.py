"""
AI Service Layer - Evals - Evaluation Service (Sprint 8)
OMS-360 Enterprise Food Delivery Platform

EvaluationService is a thin, capability-gated layer over EvalRunner +
EvaluationReportBuilder, mirroring the Router/Server-style splits from
Sprint 6 (MCPRequestRouter/MCPServer) and Sprint 7
(AgentOrchestrator/AgentService): EvalRunner owns pure execution
mechanics and has no knowledge of enablement; EvaluationService adds the
existing AIService.require_capability("evals_enabled") gate on top of
it, then hands the raw EvalReport to EvaluationReportBuilder for the
consolidated summary.
"""

from ai.evals.base import EvalReport
from ai.evals.reports import EvaluationReportBuilder, EvaluationSummary
from ai.evals.runner import EvalRunner
from ai.services.ai_service import AIService

_CAPABILITY = "evals_enabled"


class EvaluationService:
    def __init__(self, runner: EvalRunner, report_builder: EvaluationReportBuilder, ai_service: AIService):
        self._runner = runner
        self._report_builder = report_builder
        self._ai_service = ai_service

    async def evaluate(self, cases: list, target) -> EvaluationSummary:
        self._ai_service.require_capability(_CAPABILITY)
        report: EvalReport = await self._runner.run(cases, target)
        return self._report_builder.build(report)
