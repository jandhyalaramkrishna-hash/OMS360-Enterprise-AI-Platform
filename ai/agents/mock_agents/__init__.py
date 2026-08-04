"""
AI Service Layer - Agents - Mock Agents (Sprint 7)
OMS-360 Enterprise Food Delivery Platform

Six mock agents mirroring the order lifecycle: OrderAgent,
InventoryAgent, KitchenAgent, DeliveryAgent, CustomerSupportAgent,
AnalyticsAgent. Every agent returns fully deterministic, mock-only data
(no real AI model, no Kafka, no database) and, where it makes sense in
the lifecycle, publishes a mock AgentMessage to the next agent via the
shared AgentMessageBus (ai/agents/messaging.py) - see AgentFactory
(factory.py) for how they are assembled with a bus injected.
"""
