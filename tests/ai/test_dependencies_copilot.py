"""
Tests for the AI Copilot additions to ai/dependencies.py — singleton
wiring and the copilot_enabled runtime flag, following the same pattern
tests/ai/test_dependencies_sprint2.py through _sprint9.py already use
for each prior sprint's own dependencies additions.
"""

from ai.copilot.business_insights_service import BusinessInsightsService
from ai.copilot.business_qa_service import BusinessQAService
from ai.copilot.documentation_assistant_service import DocumentationAssistantService
from ai.copilot.executive_summary_service import ExecutiveSummaryService
from ai.copilot.learning_assistant_service import LearningAssistantService
from ai.copilot.provider_manager import AIProviderManager
from ai.copilot.qa_assistant_service import QAAssistantService
from ai.copilot.root_cause_service import RootCauseAnalysisService
from ai.dependencies import (
    get_business_insights_service,
    get_business_qa_service,
    get_copilot_runtime_config,
    get_documentation_assistant_service,
    get_executive_summary_service,
    get_learning_assistant_service,
    get_provider_manager,
    get_provider_registry,
    get_qa_assistant_service,
    get_root_cause_service,
)
from ai.runtime.config import RuntimeConfiguration, load_runtime_configuration


def test_get_provider_manager_returns_singleton_of_correct_type():
    manager = get_provider_manager()
    assert isinstance(manager, AIProviderManager)
    assert get_provider_manager() is manager


def test_provider_manager_shares_the_same_registry_singleton_as_the_rest_of_ai_runtime():
    # "one shared collaborator" (DEC-0017 through DEC-0022) - the copilot
    # provider manager must not build its own, second ProviderRegistry.
    manager = get_provider_manager()
    assert manager._registry is get_provider_registry()


def test_get_business_qa_service_returns_singleton_of_correct_type():
    service = get_business_qa_service()
    assert isinstance(service, BusinessQAService)
    assert get_business_qa_service() is service


def test_get_executive_summary_service_returns_singleton_of_correct_type():
    service = get_executive_summary_service()
    assert isinstance(service, ExecutiveSummaryService)
    assert get_executive_summary_service() is service


def test_get_business_insights_service_returns_singleton_of_correct_type():
    service = get_business_insights_service()
    assert isinstance(service, BusinessInsightsService)
    assert get_business_insights_service() is service


def test_get_copilot_runtime_config_defaults_enabled_true():
    config = get_copilot_runtime_config()
    assert isinstance(config, RuntimeConfiguration)
    assert config.copilot_enabled is True


def test_copilot_enabled_respects_env_override(monkeypatch):
    # get_copilot_runtime_config() reads through RuntimeConfigLoader, a
    # process-lifetime singleton (ai/runtime/loader.py) that caches its
    # first load - exactly like every other ai.dependencies.get_*()
    # config accessor. That caching is correct, existing Sprint 2
    # behavior, not something to route around here; the env-override
    # itself is verified directly against the pure, uncached
    # load_runtime_configuration() function instead, matching how
    # tests/ai/test_runtime_config.py already tests every other flag.
    monkeypatch.setenv("COPILOT_ENABLED", "false")
    config = load_runtime_configuration()
    assert config.copilot_enabled is False


def test_copilot_enabled_is_independent_of_ai_enabled():
    # ai_enabled defaults False in this environment (no AI_API_KEY set),
    # yet copilot_enabled must still default True - the entire point of
    # RuntimeConfiguration.copilot_enabled being its own field rather
    # than folded into is_capability_enabled().
    config = get_copilot_runtime_config()
    assert config.ai_enabled is False
    assert config.copilot_enabled is True


# --- AI Copilot Sprint 2 additions (Root Cause, QA Assistant, Docs
# Assistant, Learning Assistant) --------------------------------------------

def test_get_root_cause_service_returns_singleton_of_correct_type():
    service = get_root_cause_service()
    assert isinstance(service, RootCauseAnalysisService)
    assert get_root_cause_service() is service
    assert service._provider_manager is get_provider_manager()


def test_get_qa_assistant_service_returns_singleton_of_correct_type():
    service = get_qa_assistant_service()
    assert isinstance(service, QAAssistantService)
    assert get_qa_assistant_service() is service
    assert service._provider_manager is get_provider_manager()


def test_get_documentation_assistant_service_returns_singleton_of_correct_type():
    service = get_documentation_assistant_service()
    assert isinstance(service, DocumentationAssistantService)
    assert get_documentation_assistant_service() is service
    assert service._provider_manager is get_provider_manager()


def test_get_learning_assistant_service_returns_singleton_of_correct_type():
    service = get_learning_assistant_service()
    assert isinstance(service, LearningAssistantService)
    assert get_learning_assistant_service() is service
    assert service._provider_manager is get_provider_manager()
