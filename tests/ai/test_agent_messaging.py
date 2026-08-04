"""
Tests for ai/agents/messaging.py — AgentMessage / AgentMessageBus: a mock,
in-process message log appended directly to AgentContext.messages.
"""

from ai.agents.base import AgentContext
from ai.agents.messaging import AgentMessage, AgentMessageBus


def test_publish_appends_message_to_context():
    context = AgentContext(input="hi")
    bus = AgentMessageBus()

    message = bus.publish(context, "sender_agent", "recipient_agent", "did_a_thing", {"k": "v"})

    assert isinstance(message, AgentMessage)
    assert context.messages == [message]
    assert message.sender == "sender_agent"
    assert message.recipient == "recipient_agent"
    assert message.content == "did_a_thing"
    assert message.data == {"k": "v"}


def test_publish_defaults_data_to_empty_dict():
    context = AgentContext(input="hi")
    bus = AgentMessageBus()
    message = bus.publish(context, "a", "b", "content")
    assert message.data == {}


def test_messages_for_filters_by_recipient():
    context = AgentContext(input="hi")
    bus = AgentMessageBus()
    bus.publish(context, "a", "kitchen_agent", "m1")
    bus.publish(context, "b", "delivery_agent", "m2")
    bus.publish(context, "c", "kitchen_agent", "m3")

    for_kitchen = bus.messages_for(context, "kitchen_agent")
    assert [m.content for m in for_kitchen] == ["m1", "m3"]


def test_messages_for_empty_when_no_match():
    context = AgentContext(input="hi")
    bus = AgentMessageBus()
    bus.publish(context, "a", "kitchen_agent", "m1")
    assert bus.messages_for(context, "nobody") == []


def test_agent_context_defaults_messages_to_empty_list():
    context = AgentContext(input="hi")
    assert context.messages == []
