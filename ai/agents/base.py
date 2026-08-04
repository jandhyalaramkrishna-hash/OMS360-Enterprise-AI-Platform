"""
AI Service Layer - Agents - Agent interface
OMS-360 Enterprise Food Delivery Platform
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentContext:
    """Shared state passed between agents during a run. `history` records
    each agent's contribution, in order, for traceability/debugging.

    `messages` (Sprint 7 addition): the mock agent-to-agent message log
    for this run. AgentMessageBus.publish() appends AgentMessage entries
    here as agents run; it defaults to an empty list so every existing
    AgentContext(input=...) construction from Sprint 1 remains valid
    unchanged."""
    input: str
    data: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    messages: list = field(default_factory=list)


class AgentBase(ABC):
    """Contract every agent must implement. `name` must be unique within
    an AgentOrchestrator's registry."""

    name: str

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentContext:
        """Process the context and return it (mutated or replaced)."""
        raise NotImplementedError
