"""
AI Service Layer - Runtime Configuration Loader
OMS-360 Enterprise Food Delivery Platform

Single entry point for obtaining a validated RuntimeConfiguration.
Process-lifetime singleton, mirroring the DI-provider pattern used in
ai/dependencies.py (Sprint 1).
"""

from app.core.logging_config import get_logger

from ai.runtime.config import RuntimeConfiguration, load_runtime_configuration
from ai.runtime.validation import ValidationResult, validate_runtime_configuration

logger = get_logger("ai.runtime")


class RuntimeConfigLoader:
    def __init__(self):
        self._config = None
        self._validation = None

    def load(self, force_reload: bool = False) -> RuntimeConfiguration:
        if self._config is None or force_reload:
            self._config = load_runtime_configuration()
            self._validation = validate_runtime_configuration(self._config)
            logger.info(
                "Runtime configuration loaded",
                extra={
                    "ctx_ai_enabled": self._config.ai_enabled,
                    "ctx_provider_name": self._config.provider_name or "-",
                    "ctx_error_count": len(self._validation.errors),
                    "ctx_warning_count": len(self._validation.warnings),
                },
            )
            for warning in self._validation.warnings:
                logger.warning(warning)
            for error in self._validation.errors:
                logger.error(error)
        return self._config

    def validation(self) -> ValidationResult:
        if self._validation is None:
            self.load()
        return self._validation


_loader = RuntimeConfigLoader()


def get_runtime_config_loader() -> RuntimeConfigLoader:
    return _loader
