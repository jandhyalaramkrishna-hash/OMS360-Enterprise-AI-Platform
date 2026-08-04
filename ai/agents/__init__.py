"""
AI Service Layer - Multi-agent orchestration.

Sprint 1: AgentBase/AgentContext (base.py), AgentOrchestrator
(orchestrator.py) - unchanged in shape, still directly usable.

Sprint 7 additions: AgentRegistry (registry.py, now composed by
AgentOrchestrator instead of an internal dict), AgentMessage/
AgentMessageBus (messaging.py, mock agent-to-agent messaging),
AgentHealthChecker (health.py), AgentFactory (factory.py), AgentService
(agent_service.py, capability-gated wrapper), and six mock agents under
mock_agents/ (Order, Inventory, Kitchen, Delivery, Customer Support,
Analytics). See README.md for the full pipeline and DEC-0020.
"""
