"""
OMS-360 Enterprise Order Management System - Version 1.0
Central application configuration.

Single source of truth for DB connection, Kafka bootstrap servers, and topic
names. Every other module (database.py, messaging/*, routes/*) reads from
`settings` here rather than hardcoding values.
"""

import os

from dotenv import load_dotenv

# Loads a .env file from the project root if present. In Docker/production,
# real env vars (set via `docker run -e` / compose `environment:` /
# your CI secrets) take precedence automatically - load_dotenv() does NOT
# override already-set environment variables by default.
load_dotenv()


class ApplicationSettings:
    # Service info
    APP_VERSION: str = "1.1"
    APP_NAME: str = "OMS-360 Enterprise Order Management Engine"
    BUILD_VERSION: str = os.getenv("OMS360_BUILD_VERSION", "dev-local")

    # Application environment / runtime mode (Requirement #13)
    APP_ENV: str = os.getenv("OMS360_APP_ENV", "development")   # development|staging|production
    LOG_LEVEL: str = os.getenv("OMS360_LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("OMS360_DEBUG_MODE", "false").lower() == "true"
    DOCKER_MODE: bool = os.getenv("OMS360_DOCKER_MODE", "false").lower() == "true"

    # Feature flags - toggle features without a redeploy. Extend this dict
    # as new optional features are added; routes/services should check
    # `settings.FEATURE_FLAGS.get("flag_name", False)` rather than importing
    # a new standalone constant each time.
    FEATURE_FLAGS: dict = {
        "inventory_ledger_enabled": os.getenv("OMS360_FEATURE_INVENTORY_LEDGER", "true").lower() == "true",
        "dashboard_analytics_enabled": os.getenv("OMS360_FEATURE_DASHBOARD_ANALYTICS", "true").lower() == "true",
        "notifications_enabled": os.getenv("OMS360_FEATURE_NOTIFICATIONS", "false").lower() == "true",
        # AI features are explicitly V2 scope (see the Understanding
        # Document, Section 1) - flags exist so routes can check them and
        # return a clean "not enabled" response later, but nothing reads
        # this as true in V1.
        "ai_features_enabled": False,
    }

    # Timeouts (seconds)
    DB_QUERY_TIMEOUT_SECONDS: int = int(os.getenv("OMS360_DB_TIMEOUT_SECONDS", "10"))
    KAFKA_PUBLISH_TIMEOUT_SECONDS: float = float(os.getenv("OMS360_KAFKA_PUBLISH_TIMEOUT", "5.0"))
    HTTP_CLIENT_TIMEOUT_SECONDS: float = float(os.getenv("OMS360_HTTP_TIMEOUT", "10.0"))

    # Notification channels - placeholders. Nothing currently sends real
    # email/SMS (notifications_enabled defaults to false); these exist so
    # NotificationService (app/services/notification_service.py) has
    # somewhere to read config from once a real provider is wired in.
    EMAIL_SMTP_HOST: str = os.getenv("OMS360_EMAIL_SMTP_HOST", "")
    EMAIL_SMTP_PORT: int = int(os.getenv("OMS360_EMAIL_SMTP_PORT", "587"))
    EMAIL_FROM_ADDRESS: str = os.getenv("OMS360_EMAIL_FROM", "")
    SMS_PROVIDER: str = os.getenv("OMS360_SMS_PROVIDER", "")
    SMS_API_KEY: str = os.getenv("OMS360_SMS_API_KEY", "")

    # 2026-08-28 addition: SMTP auth + the fixed alert recipient for the
    # inventory low-stock ("Danger Level") email alert. Reuses the
    # EMAIL_SMTP_HOST/PORT/FROM settings above and the existing
    # notifications_enabled feature flag - notification_service.py is the
    # only place these are read, and the alert is only ever raised from the
    # existing inventory_service.py low-stock/out-of-stock path.
    EMAIL_SMTP_USERNAME: str = os.getenv("OMS360_EMAIL_SMTP_USERNAME", "")
    EMAIL_SMTP_PASSWORD: str = os.getenv("OMS360_EMAIL_SMTP_PASSWORD", "")
    INVENTORY_ALERT_EMAIL: str = os.getenv("OMS360_INVENTORY_ALERT_EMAIL", "jandhyala.ramkrishna@gmail.com")

    # 2026-11-20 addition (low-stock email fix): SMTP socket timeout, and
    # the minimum gap before an alert whose email FAILED is automatically
    # retried again by ordinary stock processing (so a broken SMTP setup
    # can't add an SMTP round-trip to every single order). The manual
    # POST /api/v1/inventory/alerts/dispatch-pending endpoint ignores the
    # cooldown.
    EMAIL_SMTP_TIMEOUT_SECONDS: float = float(os.getenv("OMS360_EMAIL_SMTP_TIMEOUT", "10"))
    NOTIFICATION_RETRY_COOLDOWN_SECONDS: int = int(os.getenv("OMS360_NOTIFICATION_RETRY_COOLDOWN_SECONDS", "300"))

    # GPS / delivery tracking - placeholder for future live tracking (V2 roadmap)
    GPS_PROVIDER: str = os.getenv("OMS360_GPS_PROVIDER", "")
    GPS_API_KEY: str = os.getenv("OMS360_GPS_API_KEY", "")

    # Future AI configuration - placeholder only. See the Understanding
    # Document and TEST_PLAN.md Section 6 for why this is explicitly out of
    # scope for V1. Reading these values does not enable any AI behavior.
    AI_PROVIDER: str = os.getenv("OMS360_AI_PROVIDER", "")       # e.g. "ollama" | "openai" (V2)
    AI_MODEL_NAME: str = os.getenv("OMS360_AI_MODEL_NAME", "")
    AI_API_KEY: str = os.getenv("OMS360_AI_API_KEY", "")

    # Relational Database Constraints
    DB_HOST: str = os.getenv("OMS360_DB_HOST", "127.0.0.1")       # Use 127.0.0.1 to force local TCP routing
    DB_PORT: int = int(os.getenv("OMS360_DB_PORT", "3306"))
    DB_USER: str = os.getenv("OMS360_DB_USER", "root")
    DB_PASSWORD: str = os.getenv("OMS360_DB_PASSWORD", "root123") # Change "password" to "root123"
    DB_NAME: str = os.getenv("OMS360_DB_NAME", "oms360_db")
    DB_POOL_SIZE: int = int(os.getenv("OMS360_DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("OMS360_DB_MAX_OVERFLOW", "20"))

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_ENABLED: bool = os.getenv("OMS360_KAFKA_ENABLED", "true").lower() == "true"
    KAFKA_CONSUMER_GROUP: str = os.getenv("OMS360_KAFKA_GROUP", "oms360-fulfillment-service")

    # Topic taxonomy - the ONE authoritative list. Producer and consumer both
    # import these instead of hardcoding topic strings.
    TOPIC_ORDER_CREATED: str = "order.created"
    TOPIC_PAYMENT_COMPLETED: str = "payment.completed"
    TOPIC_PAYMENT_FAILED: str = "payment.failed"
    TOPIC_KITCHEN_ACCEPTED: str = "kitchen.accepted"
    TOPIC_KITCHEN_REJECTED: str = "kitchen.rejected"
    TOPIC_DELIVERY_ASSIGNED: str = "delivery.assigned"
    TOPIC_DELIVERY_COMPLETED: str = "delivery.completed"
    TOPIC_INVENTORY_UPDATED: str = "inventory.updated"
    TOPIC_NOTIFICATION_SENT: str = "notification.sent"
    TOPIC_ORDER_DLQ: str = "order.dlq"
    TOPIC_ORDER_RETRY: str = "order.retry"

    # Resiliency
    MAX_RETRY_COUNT: int = 3
    RETRY_DELAY_SECONDS: int = 5

    # Idempotency: duplicate_orders (per oms360_schema.sql) has no hash/key
    # column to persist a request fingerprint against, so duplicate
    # detection for a given idempotency key is done via an in-process TTL
    # cache in order_service.py, valid for this many seconds. Documented
    # limitation: this does NOT survive a process restart or work across
    # multiple app instances - a real fix would need a schema change
    # (e.g. a `request_hash` column), which is out of scope until you
    # approve one.
    DUPLICATE_CACHE_TTL_SECONDS: int = 300

    # Kitchen/delivery simulation timing (used by the consumer to make the
    # demo visibly progress instead of instantly completing every order)
    SIM_COOKING_SECONDS: int = int(os.getenv("OMS360_SIM_COOKING_SECONDS", "8"))
    SIM_DELIVERY_SECONDS: int = int(os.getenv("OMS360_SIM_DELIVERY_SECONDS", "12"))

    METRICS_ENABLED: bool = True


settings = ApplicationSettings()
