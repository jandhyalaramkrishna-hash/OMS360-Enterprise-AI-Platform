"""
OMS-360 Enterprise Order Management System - Version 1.1
Centralized structured logging (Requirement #8).

Every log line is JSON and automatically includes, when set:
  request_id, transaction_id, order_id, user_id, session_id,
  kafka_topic, kafka_offset, consumer_group, correlation_id,
  environment, hostname, ip_address
plus per-call fields (stage, execution_time_ms, api_name, etc.) passed via
`extra={"ctx_<name>": value}` or the `log_stage()` helper.

user_id / session_id are contextvars ready for when this project adds
authentication (there's no auth system yet - see the understanding
document) - they default to "-" and cost nothing to carry now.
"""

import contextvars
import json
import logging
import socket
import sys
import time
from datetime import datetime, timezone

from app.config import settings

# --- Context variables, correct across async requests ----------------------
request_id_var = contextvars.ContextVar("request_id", default="-")
transaction_id_var = contextvars.ContextVar("transaction_id", default="-")
order_id_var = contextvars.ContextVar("order_id", default="-")
user_id_var = contextvars.ContextVar("user_id", default="-")
session_id_var = contextvars.ContextVar("session_id", default="-")
kafka_topic_var = contextvars.ContextVar("kafka_topic", default="-")
kafka_offset_var = contextvars.ContextVar("kafka_offset", default="-")
consumer_group_var = contextvars.ContextVar("consumer_group", default="-")
correlation_id_var = contextvars.ContextVar("correlation_id", default="-")
ip_address_var = contextvars.ContextVar("ip_address", default="-")

_HOSTNAME = socket.gethostname()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.APP_ENV,
            "hostname": _HOSTNAME,
            "request_id": request_id_var.get(),
            "correlation_id": correlation_id_var.get(),
            "transaction_id": transaction_id_var.get(),
            "order_id": order_id_var.get(),
            "user_id": user_id_var.get(),
            "session_id": session_id_var.get(),
            "ip_address": ip_address_var.get(),
        }
        if kafka_topic_var.get() != "-":
            payload["kafka_topic"] = kafka_topic_var.get()
            payload["kafka_offset"] = kafka_offset_var.get()
            payload["consumer_group"] = consumer_group_var.get()

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                payload[key[4:]] = value
        return json.dumps(payload, default=str)


def configure_logging(level: int = None):
    root = logging.getLogger()
    root.setLevel(level or getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_stage(order_id: str, transaction_id: str, stage: str, logger: logging.Logger = None,
              api_name: str = None, execution_time_ms: float = None, **extra):
    """Logs one pipeline-stage transition with full context.
    Stages: ORDER_CREATED, PAYMENT_PENDING, PAYMENT_SUCCESS, PAYMENT_FAILED,
    INVENTORY_RESERVED, KITCHEN_STARTED, KITCHEN_COMPLETED,
    OUT_FOR_DELIVERY, DELIVERED, ORDER_FAILED, DUPLICATE_REJECTED - see
    app.core.enums.AuditEventType for the authoritative list.
    """
    logger = logger or get_logger("oms360.pipeline")
    order_id_var.set(order_id or "-")
    transaction_id_var.set(transaction_id or "-")

    ctx = {"ctx_stage": stage}
    if api_name:
        ctx["ctx_api_name"] = api_name
    if execution_time_ms is not None:
        ctx["ctx_execution_time_ms"] = round(execution_time_ms, 2)
    ctx.update({f"ctx_{k}": v for k, v in extra.items()})

    logger.info(f"STAGE={stage}", extra=ctx)


def log_kafka_event(logger: logging.Logger, topic: str, offset, consumer_group: str,
                     message: str, execution_time_ms: float = None):
    """Sets Kafka-specific context for the duration of one log call. Callers
    in messaging/consumer.py use this so every consume-side log line carries
    topic/offset/consumer_group without threading them through every
    function signature."""
    kafka_topic_var.set(topic)
    kafka_offset_var.set(str(offset) if offset is not None else "-")
    consumer_group_var.set(consumer_group or "-")
    extra = {}
    if execution_time_ms is not None:
        extra["ctx_execution_time_ms"] = round(execution_time_ms, 2)
    logger.info(message, extra=extra)


class Timer:
    """Small context manager for measuring execution_time_ms cleanly:
        with Timer() as t:
            ...
        log_stage(..., execution_time_ms=t.elapsed_ms)
    """
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
