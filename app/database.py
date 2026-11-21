"""
OMS-360 Enterprise Order Management System - Version 1.0
Database persistence layer.

NOTE ON A DELIBERATE CHANGE FROM THE OLD database.py:
The previous version of this file ran CREATE TABLE / ALTER TABLE statements
automatically on import (`execute_instant_schema_patch()`), as a side effect
of just importing the module. That's removed here. The schema is now owned
by oms360_schema.sql (the master schema, per your instruction) and applied
once via that script - the application should never silently mutate its own
schema on startup. If you want an explicit, opt-in "create tables if missing"
helper for local dev, `init_db()` below does that, but it is NOT called
automatically - something has to call it on purpose (see scripts below).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import os

from app.config import settings

# Optional TLS for managed cloud MySQL (e.g. TiDB Cloud, which requires it).
# Off by default, so local MySQL/Docker behaviour is unchanged. Enable with
# OMS360_DB_SSL=true; certificates are verified against the certifi CA bundle.
# 2026-11-22: the flag is trimmed, so "true " pasted with a trailing space
# still enables TLS instead of silently connecting without it.
def build_connect_args() -> dict:
    if os.getenv("OMS360_DB_SSL", "false").strip().lower() == "true":
        import certifi
        return {"ssl": {"ca": certifi.where()}}
    return {}


_connect_args = build_connect_args()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=3600,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_pool_stats() -> dict:
    """Used by GET /health (Requirement #6: 'Database Pool')."""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }


def get_db():
    """FastAPI dependency - yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Explicit, opt-in table creation for local/dev use only.
    Does NOT run automatically on import. Call it yourself, e.g.:
        python -m app.database
    In any environment where oms360_schema.sql has already been applied
    (which it should have been, per the master-schema decision), this is a
    no-op - create_all only creates tables that don't already exist, it never
    alters existing ones.
    """
    import app.models  # noqa: F401  (ensure models are registered on Base)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("[database.py] init_db() complete (created any missing tables only).")
