"""
OMS-360 Enterprise Order Management System - Version 1.1
Dedicated business exceptions (Requirement #9) + the global exception
handler architecture (unchanged from V1 - still the single place that
turns any exception into a consistent JSON response).

Every response body has the same shape:
    {"error": "<short code>", "detail": "<message>", "request_id": "<id>"}
Full stack traces are always logged internally (logger.exception), never
put in the HTTP response body.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging_config import get_logger, request_id_var
from app.core import metrics

logger = get_logger("oms360.errors")


class OMSBusinessError(Exception):
    """Base class for every dedicated business exception below. Expected,
    business-level errors (not bugs) - logged at WARNING, no stack trace in
    the response, and formatted consistently by business_error_handler."""
    status_code = 400
    error_code = "business_error"

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


# --- Dedicated business exceptions (Requirement #9) ------------------------

class DuplicateOrderException(OMSBusinessError):
    status_code = 409
    error_code = "duplicate_order"

    def __init__(self, existing_order_id: str):
        self.existing_order_id = existing_order_id
        super().__init__(f"Duplicate request detected (original order_id={existing_order_id})")


class PaymentFailedException(OMSBusinessError):
    status_code = 402
    error_code = "payment_failed"


class InventoryLockException(OMSBusinessError):
    """Raised when a stock row can't be locked/updated safely (e.g. a
    concurrent modification conflict beyond normal insufficient-stock)."""
    status_code = 409
    error_code = "inventory_lock_error"


class InventoryNotFoundException(OMSBusinessError):
    status_code = 404
    error_code = "inventory_not_found"


class UnknownItemException(OMSBusinessError):
    status_code = 400
    error_code = "unknown_item"


class OrderNotFoundException(OMSBusinessError):
    status_code = 404
    error_code = "order_not_found"


class KafkaPublishException(OMSBusinessError):
    """Note: publish_event() in messaging/producer.py already retries and
    falls back to dlq_orders internally rather than raising - this
    exception exists for callers/tests that want to treat a total publish
    failure as an explicit error rather than a silently-logged one."""
    status_code = 502
    error_code = "kafka_publish_error"


class KafkaConsumeException(OMSBusinessError):
    status_code = 502
    error_code = "kafka_consume_error"


class DatabaseConnectionException(OMSBusinessError):
    status_code = 503
    error_code = "database_connection_error"


# Backward-compat aliases: the V1 code (order_service.py before this
# refactor) used these shorter names. Keeping them as aliases means nothing
# that imported the old names breaks, while new code uses the spec names.
InsufficientStockError = InventoryLockException
DuplicateOrderError = DuplicateOrderException
UnknownItemError = UnknownItemException


def _error_body(error_code: str, detail: str) -> dict:
    return {"error": error_code, "detail": detail, "request_id": request_id_var.get()}


def _sanitize_validation_errors(errors: list) -> list:
    """pydantic v2's exc.errors() puts the raw exception object at
    ctx.error for any field_validator that raises a plain ValueError/
    AssertionError (e.g. InventoryUpdateRequest.status, AddressPayload.
    pincode, OrderCreatePayload.mobile) - and a raw exception object isn't
    JSON-serializable, so returning it as-is crashes JSONResponse.render()
    with a 500 instead of the intended 422. Stringify ctx.error only;
    every other field (type/loc/msg/input) is already JSON-safe."""
    sanitized = []
    for err in errors:
        err = dict(err)
        ctx = err.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            err["ctx"] = {**ctx, "error": str(ctx["error"])}
        sanitized.append(err)
    return sanitized


def register_exception_handlers(app):

    @app.exception_handler(OMSBusinessError)
    async def business_error_handler(request: Request, exc: OMSBusinessError):
        logger.warning(f"Business error on {request.url.path}: {exc.detail}")
        metrics.increment("business_errors_total")
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.error_code, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.info(f"Validation error on {request.url.path}: {exc.errors()}")
        metrics.increment("validation_errors_total")
        body = _error_body("validation_error", "Invalid request payload.")
        body["fields"] = _sanitize_validation_errors(exc.errors())
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        level = logger.warning if exc.status_code < 500 else logger.error
        level(f"HTTPException {exc.status_code} on {request.url.path}: {exc.detail}")
        return JSONResponse(status_code=exc.status_code, content=_error_body("http_error", str(exc.detail)))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
        metrics.increment("unhandled_errors_total")
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "An unexpected error occurred. It has been logged."),
        )
