"""
OMS-360 Enterprise Order Management System - Version 1.0
THE authoritative FastAPI entry point.

Per your decision: this replaces api_gateway.py and the old standalone
main.py as the single source of truth for the API. Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

V1.1 addition: serves the two Enterprise Dashboard HTML pages
(Operations Center, Monitoring Center) as static files at
/dashboard/operations and /dashboard/monitoring. They are plain HTML/CSS/JS
that call the existing (and newly added) JSON APIs under /api/v1/dashboard
- no template engine dependency added, nothing here changes any existing
route's behavior.

Sprint 3 addition: registers app/api/ai/router.py under /api/v1/ai - six
read-only introspection endpoints over the Sprint 2 AI Runtime (see
app/api/ai/README.md). This is the only other change in this file; no
existing route, middleware, or handler registration below was touched.

2026-07-22 addition: serves a third Enterprise Dashboard HTML page,
app/static/inventory_dashboard.html, at /dashboard/inventory - same
pattern as the two above (plain HTML/CSS/JS calling the existing
GET /api/v1/inventory endpoint, no new backend route needed for the page
itself). Added as its own function rather than editing the two existing
page handlers, so operations/monitoring routes are untouched.

2026-07-22 fix (see docs/governance/DECISION-LOG.md, DEC-0032): the three
dashboard page routes below now explicitly set Cache-Control: no-store.
FileResponse's default headers (Last-Modified/ETag, no explicit
Cache-Control) let browsers heuristically cache these pages - after the
Inventory nav link was added to all three pages, a user could still see
a stale, pre-fix copy of a page they'd already loaded/cached earlier in
the session (Inventory link missing), even though the server was already
serving the corrected file. Forcing no-store means every navigation
between dashboards always fetches the current file from the server -
these pages are cheap to re-fetch (they're a few KB of HTML) and are
expected to change between deployments, so there's no caching benefit
worth the staleness risk. The one-time /dashboard/assets StaticFiles
mount (unused by any current page, kept for future shared assets) is
intentionally NOT touched by this fix.

AI Copilot Sprint 1 / Phase 1 addition (see docs/governance/DECISION-LOG.md,
DEC-0033 onward): registers app/api/ai/copilot_router.py under
/api/v1/ai/copilot, and serves a fourth Enterprise Dashboard HTML page,
app/static/ai_copilot.html, at /dashboard/ai-copilot - same
FileResponse + no-store pattern as the three pages above. The existing
/api/v1/ai router (Sprint 3, six read-only introspection endpoints) is
untouched; AI Copilot is an additive, separate router.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.logging_config import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.exceptions import register_exception_handlers
from app.routes import health, orders, inventory, dashboard, metrics
from app.api.ai.router import router as ai_router
from app.api.ai.copilot_router import router as ai_copilot_router

configure_logging()

# TEMPORARY (2026-11-22): one-line, secret-free database configuration
# diagnostic for the production 1045 investigation - see app/core/db_diagnostics.py.
from app.core.db_diagnostics import log_db_diagnostic  # noqa: E402
log_db_diagnostic()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Single authoritative API for OMS-360. api_gateway.py and the old "
        "standalone main.py are legacy/demo code as of this version. "
        "See README.md and the OMS-360 Understanding Document for full context."
    ),
    contact={"name": "OMS-360 Project"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(orders.router)
app.include_router(inventory.router)
app.include_router(dashboard.router)
app.include_router(metrics.router)
app.include_router(ai_router)
app.include_router(ai_copilot_router)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/dashboard/assets", StaticFiles(directory=_STATIC_DIR), name="dashboard-assets")

# See the module docstring (2026-07-22 fix / DEC-0032): every dashboard page
# is served with Cache-Control: no-store so a browser never shows a stale
# cached copy of one page's nav bar (or anything else) after a deploy.
_NO_CACHE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate"}


@app.get("/dashboard/operations", include_in_schema=False, summary="Operations Center dashboard (HTML)")
def operations_dashboard_page():
    return FileResponse(os.path.join(_STATIC_DIR, "operations_dashboard.html"), headers=_NO_CACHE_HEADERS)


@app.get("/dashboard/monitoring", include_in_schema=False, summary="Monitoring Center dashboard (HTML)")
def monitoring_dashboard_page():
    return FileResponse(os.path.join(_STATIC_DIR, "monitoring_dashboard.html"), headers=_NO_CACHE_HEADERS)


@app.get("/dashboard/inventory", include_in_schema=False, summary="Inventory Center dashboard (HTML)")
def inventory_dashboard_page():
    return FileResponse(os.path.join(_STATIC_DIR, "inventory_dashboard.html"), headers=_NO_CACHE_HEADERS)


@app.get("/dashboard/ai-copilot", include_in_schema=False, summary="AI Copilot dashboard (HTML)")
def ai_copilot_dashboard_page():
    return FileResponse(os.path.join(_STATIC_DIR, "ai_copilot.html"), headers=_NO_CACHE_HEADERS)


@app.get("/dashboard", include_in_schema=False)
def dashboard_index():
    return RedirectResponse(url="/dashboard/operations")
