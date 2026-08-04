"""
AI Copilot - AI Learning Assistant Service
OMS-360 Enterprise Food Delivery Platform

LearningAssistantService ships its own small, hand-written, factually
accurate knowledge base (_TOPICS below) describing how OMS-360 actually
works - not an LLM's general knowledge about food delivery systems in the
abstract. Each topic's text was written from reading the real modules it
describes (app/messaging/producer.py, app/messaging/consumer.py,
app/services/inventory_service.py, app/services/kitchen_service.py,
app/services/delivery_service.py, app/routes/health.py,
app/routes/metrics.py, app/models.py) - this is the single source of
truth for "what topics exist" and "what is factually true about each
one."

An LLM, if a real provider is configured (via the SAME shared
AIProviderManager every other AI Copilot service uses), may only
elaborate/rephrase a topic's existing text (same "reword, don't invent"
discipline as BusinessQAService._reword) or, for ask(), pick the nearest
matching topic via simple keyword matching and elaborate on THAT topic's
real text - it is never allowed to answer from general knowledge about
unrelated systems. If no provider is configured, or a provider call
fails for any reason, the hand-written topic text is returned as-is -
this is the default mode, not a degraded one.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.core.logging_config import get_logger

from ai.copilot.provider_manager import AIProviderManager
from ai.core.exceptions import AICopilotLearningTopicNotFoundError

logger = get_logger("ai.copilot.learning_assistant")


# Topic key -> (display title, factual explanation, alias keywords used by
# ask()'s simple matcher). Every sentence below is grounded in what this
# repository's own modules actually do - see the module docstring for the
# files each topic was written from.
_TOPICS = {
    "architecture": (
        "System Architecture",
        (
            "OMS-360 is an event-driven FastAPI application backed by MySQL and Apache Kafka. "
            "A REST API (app/routes/orders.py) accepts a customer order, validates and locks "
            "inventory, writes orders_master/order_items/transactions in one transaction, creates "
            "initial kitchen_status/delivery_status rows, records an audit trail entry, and "
            "publishes an order.created Kafka event. A separate Kafka consumer process "
            "(app/messaging/consumer.py) then orchestrates the order through the remaining "
            "modules in sequence: KitchenService (cooking simulation), PaymentService, "
            "DeliveryService, and NotificationService, with AuditService recording every "
            "transition. The core enterprise modules are: Customer Order Management, "
            "Restaurant/Menu/Inventory Management, Kitchen Processing, Payment Processing, "
            "Kafka Event Processing, Delivery Management, Notification Service, Audit Trail, "
            "Retry & Dead Letter Queue handling, and Health/Metrics monitoring."
        ),
        ("architecture", "system design", "overview", "how does this system work"),
    ),
    "kafka": (
        "Kafka Event Processing",
        (
            "app/messaging/producer.py is the single, authoritative Kafka producer: it publishes "
            "events with a retry loop (up to settings.MAX_RETRY_COUNT attempts with "
            "settings.RETRY_DELAY_SECONDS backoff), and if every retry fails it writes the event "
            "to the dlq_orders table instead of dropping it silently - a database row rather than "
            "a Kafka DLQ topic, since dlq_orders has no consumer of its own defined in this "
            "project. If Kafka is unreachable entirely, publish_event() logs and returns False "
            "instead of crashing the request. app/messaging/consumer.py is the single, "
            "authoritative consumer: it polls, parses, and calls KitchenService, PaymentService, "
            "DeliveryService, and AuditService in order for each order, and handles graceful "
            "shutdown on SIGTERM/SIGINT so an in-flight message finishes before the process exits."
        ),
        ("kafka", "event processing", "producer", "consumer", "dlq", "dead letter queue", "retry"),
    ),
    "inventory": (
        "Inventory Management",
        (
            "app/services/inventory_service.py owns everything touching the inventory, "
            "inventory_ledger, and inventory_alerts tables. lock_and_fetch() takes a row-level "
            "lock (SELECT ... FOR UPDATE) on the requested items before reserving stock, so "
            "concurrent orders can't oversell the same item. reserve_stock() decrements "
            "remaining_stock, increments used_stock, writes an inventory_ledger row for the "
            "movement, and raises InventoryLockException if requested quantity exceeds what's "
            "available. The low-stock threshold is read from system_configuration "
            "(LOW_STOCK_THRESHOLD), falling back to a default of 10 if unset, and crossing into "
            "LOW_STOCK or OUT_OF_STOCK raises a row in inventory_alerts."
        ),
        ("inventory", "stock", "low stock", "out of stock", "ledger"),
    ),
    "kitchen": (
        "Kitchen Processing",
        (
            "app/services/kitchen_service.py owns everything touching the kitchen_status table. "
            "One row is created per order item at order creation (status QUEUED), and "
            "app/messaging/consumer.py's orchestration moves each row through "
            "QUEUED -> COOKING -> READY as it processes the order (start_cooking() assigns a "
            "simulated station_id/chef_name, complete_cooking() marks it READY). "
            "get_average_cooking_time_seconds() computes the average duration from started_at to "
            "updated_at on READY rows using MySQL's TIMESTAMPDIFF - a MySQL-specific function that "
            "SQLite cannot run, which is the known, accepted gap behind this project's MySQL-only "
            "test failures."
        ),
        ("kitchen", "cooking", "chef", "station", "preparing"),
    ),
    "delivery": (
        "Delivery Management",
        (
            "app/services/delivery_service.py owns everything touching the delivery_status table. "
            "One row is created per order item (status PENDING) alongside the kitchen_status row; "
            "dispatch() (called once the matching kitchen row goes READY) moves it to "
            "OUT_FOR_DELIVERY and assigns a simulated delivery_person, and complete_delivery() "
            "marks it DELIVERED. The delivery_status table has no timestamp columns in the master "
            "schema, so get_average_delivery_time_seconds() honestly returns 0.0 / 'unavailable' "
            "rather than fabricating an average delivery duration."
        ),
        ("delivery", "rider", "out for delivery", "dispatch"),
    ),
    "monitoring": (
        "Health & Metrics Monitoring",
        (
            "GET /health (app/routes/health.py) aggregates database connectivity, Kafka broker/"
            "producer/consumer-group status, disk, memory, CPU, and Docker mode into one overall "
            "HEALTHY/WARNING/DEGRADED status - the database is treated as CRITICAL (its failure "
            "alone forces DEGRADED), while Kafka/disk/memory/CPU are NON-CRITICAL (a problem there "
            "yields WARNING only). GET /metrics (app/routes/metrics.py) reports in-memory counters "
            "(orders processed/failed/cancelled, duplicate requests, Kafka publish/consume/retry/"
            "DLQ counts, API response times) plus DB-backed totals and the 5 most recent dlq_orders "
            "rows; in-memory counters reset on restart."
        ),
        ("monitoring", "health", "metrics", "observability", "dashboard"),
    ),
    "database": (
        "Database & Data Model",
        (
            "OMS-360 uses MySQL, mapped via SQLAlchemy ORM models in app/models.py. Core tables "
            "include orders_master (one row per order), order_items (order line items), "
            "inventory (live stock, used for reservation during order placement), kitchen_status "
            "and delivery_status (one row per order item, tracking preparation/delivery progress), "
            "failed_orders and duplicate_orders (record unrecoverable processing errors and "
            "rejected duplicate/idempotent requests respectively), dlq_orders (permanently failed "
            "Kafka events), inventory_alerts (low/out-of-stock notifications), "
            "order_audit_trail (a full state-transition history per order, independent of "
            "structured application logs), and inventory_ledger (one row per stock movement: "
            "restock, reserve, release, adjustment)."
        ),
        ("database", "schema", "tables", "data model", "sql"),
    ),
}

_DEFAULT_TOPIC = "architecture"


@dataclass(frozen=True)
class LearningAnswer:
    topic: str
    title: str
    text: str
    ai_generated: bool = False


class LearningAssistantService:
    """Construct via ai.dependencies.get_learning_assistant_service(), not
    directly."""

    def __init__(self, provider_manager: AIProviderManager):
        self._provider_manager = provider_manager

    def list_topics(self) -> List[dict]:
        return [{"topic": key, "title": title} for key, (title, _text, _aliases) in _TOPICS.items()]

    async def explain_topic(self, topic: str, use_ai: bool = True) -> LearningAnswer:
        key = (topic or "").strip().lower()
        if key not in _TOPICS:
            raise AICopilotLearningTopicNotFoundError(topic)

        title, base_text, _aliases = _TOPICS[key]
        if not use_ai:
            return LearningAnswer(topic=key, title=title, text=base_text, ai_generated=False)

        selection = self._provider_manager.get_active_provider()
        if selection.provider is None:
            return LearningAnswer(topic=key, title=title, text=base_text, ai_generated=False)

        try:
            enriched = await self._elaborate(selection.provider, title, base_text)
            if enriched:
                return LearningAnswer(topic=key, title=title, text=enriched, ai_generated=True)
        except Exception:
            logger.warning("AI Copilot Learning Assistant: elaboration failed, using hand-written topic text")

        return LearningAnswer(topic=key, title=title, text=base_text, ai_generated=False)

    async def ask(self, question: str, use_ai: bool = True) -> LearningAnswer:
        key = self._match_topic(question)
        return await self.explain_topic(key, use_ai=use_ai)

    @staticmethod
    def _match_topic(question: str) -> str:
        """Simple keyword matching against topic names/aliases - similar
        spirit to ai.copilot.intents.classify_question() but simpler,
        since it only needs to pick one of a handful of topics rather than
        run a real business query."""
        normalized = (question or "").strip().lower()
        if not normalized:
            return _DEFAULT_TOPIC
        for key, (_title, _text, aliases) in _TOPICS.items():
            if key in normalized:
                return key
            for alias in aliases:
                if alias in normalized:
                    return key
        return _DEFAULT_TOPIC

    async def _elaborate(self, provider, title: str, base_text: str) -> str:
        prompt = (
            "You are a technical mentor helping a developer understand an "
            "existing system. Elaborate on the following factual "
            "explanation in clearer, friendlier language. Use ONLY the "
            "facts given below - do not invent any module, table, "
            "behavior, or architecture detail that is not stated here, "
            "and do not describe any other food-delivery system's general "
            "architecture.\n\n"
            f"Topic: {title}\n"
            f"Facts:\n{base_text}\n"
        )
        result = await provider.complete(prompt)
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        return content.strip()
