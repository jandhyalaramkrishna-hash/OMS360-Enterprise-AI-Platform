"""
AI Service Layer - Integration (Sprint 9)
OMS-360 Enterprise Food Delivery Platform

Enterprise Integration / Unified AI Workflow: composes the five AI
modules built across Sprints 1-8 (Provider Framework, RAG, MCP,
Multi-Agent, AI Evaluation) into one end-to-end call chain
(ai.integration.workflow_service.AIWorkflowService), and aggregates
health across all of them into one unified report
(ai.integration.health.PlatformHealthChecker). This package contains no
new retrieval, tool-call, agent-run, evaluation, or provider-call logic
of its own - every step is a direct call into that module's own existing,
unmodified service, reusing each one's own capability gate exactly as it
already worked standalone. See DEC-0022 and ai/integration/README.md.
"""
