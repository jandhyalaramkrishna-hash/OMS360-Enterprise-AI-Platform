"""
AI Service Layer - Agents - Mock Agent-to-Agent Messaging (Sprint 7)
OMS-360 Enterprise Food Delivery Platform

AgentMessageBus is an in-process, synchronous mock message bus: every
"message" an agent sends is simply appended to the AgentContext.messages
list it is published against. There is no real transport, queue, topic,
or network hop of any kind - this exists purely to give the six mock
agents (ai/agents/mock_agents/) a consistent, testable way to signal each
other within a single AgentOrchestrator.run_sequence() call, per the
Sprint 7 brief's explicit "mock messages only" requirement. This is not
a Kafka producer/consumer and must never become one without a separate,
explicitly-scoped sprint.
"""

from dataclasses import dataclass, field

from app.core.logging_config import get_logger

logger = get_logger("ai.agents.messaging")


@dataclass(frozen=True)
class AgentMessage:
    """One mock message exchanged between two agents during a run."""
    sender: str
    recipient: str
    content: str
    data: dict = field(default_factory=dict)


class AgentMessageBus:
    def publish(self, context, sender: str, recipient: str, content: str, data: dict = None) -> AgentMessage:
        message = AgentMessage(sender=sender, recipient=recipient, content=content, data=dict(data or {}))
        context.messages.append(message)
        logger.info(
            "Agent message published",
            extra={"ctx_sender": sender, "ctx_recipient": recipient, "ctx_content": content},
        )
        return message

    def messages_for(self, context, recipient: str) -> list:
        return [m for m in context.messages if m.recipient == recipient]
