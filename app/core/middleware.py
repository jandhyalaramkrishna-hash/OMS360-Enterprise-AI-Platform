"""
Request ID + timing middleware. Assigns a request_id to every request
(reuses an incoming X-Request-ID header if present, so this chains cleanly
behind an API gateway/load balancer that already assigns one), puts it in
logging context, echoes it back in the response header, and records timing
into app.core.metrics.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging_config import request_id_var, correlation_id_var, ip_address_var, get_logger
from app.core import metrics

logger = get_logger("oms360.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(req_id)
        correlation_id_var.set(request.headers.get("X-Correlation-ID", req_id))
        client_host = request.client.host if request.client else "-"
        ip_address_var.set(request.headers.get("X-Forwarded-For", client_host))

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.record_api_call(request.url.path, request.method, 500, duration_ms)
            logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        metrics.record_api_call(request.url.path, request.method, response.status_code, duration_ms)

        response.headers["X-Request-ID"] = req_id
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)",
            extra={"ctx_method": request.method, "ctx_path": request.url.path,
                   "ctx_status": response.status_code, "ctx_duration_ms": round(duration_ms, 1)},
        )
        return response
