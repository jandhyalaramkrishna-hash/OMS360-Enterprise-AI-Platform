"""
AI Service Layer
OMS-360 Enterprise Food Delivery Platform

Isolated AI infrastructure package. Depends inward on app/ (reusing
get_db, OMSBusinessError, get_logger) - nothing in app/ depends on this
package. Not wired into FastAPI or any existing route as of Sprint 1;
see ai/README.md for status, structure, and how to wire it in later.
"""
