"""
AI Service Layer - Services - Service registry
OMS-360 Enterprise Food Delivery Platform

Generic registry for named service instances (e.g. AIService) - distinct
from ai.mcp.registry.MCPToolRegistry (tools) and
ai.agents.orchestrator.AgentOrchestrator (agents). Exists so multiple
named service instances can be resolved by name.
"""

from app.core.logging_config import get_logger

from ai.core.exceptions import AIServiceNotFoundError

logger = get_logger("ai.services.registry")


class ServiceRegistry:
    def __init__(self):
        self._services = {}
        logger.info("ServiceRegistry initialized", extra={"ctx_service_count": 0})

    def register(self, name: str, service) -> None:
        if name in self._services:
            logger.warning("Overwriting already-registered service", extra={"ctx_service_name": name})
        self._services[name] = service
        logger.info("Service registered", extra={"ctx_service_name": name})

    def get(self, name: str):
        if name not in self._services:
            raise AIServiceNotFoundError(name)
        return self._services[name]

    def list_services(self) -> list:
        return sorted(self._services.keys())
