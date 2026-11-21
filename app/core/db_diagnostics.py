"""
TEMPORARY database-configuration diagnostic (2026-11-22, production 1045
investigation). Remove once the root cause is confirmed.

Logs ONE line per process start describing what the running engine will
actually use to connect - never the password itself:

  - host / port / user / database, read from the live SQLAlchemy engine URL
    (not re-derived from env vars, so it reflects the real configuration)
  - whether TLS is enabled for the engine, and the CA bundle path
  - the password's length and a 12-hex-character fingerprint:
        sha256(b"oms360-db-diag-v1:" + password.encode("utf-8"))[:12]
    computed on the exact (already trimmed) value the engine uses
  - whether that password is plain ASCII (PyMySQL encodes it as latin-1)
  - where each OMS360_DB_* value came from: "process environment" (Render),
    ".env file", or "code default"
  - Python / SQLAlchemy / PyMySQL versions and the process id

The same fingerprint can be computed locally (see the PowerShell command in
the change description) and compared. Disable without a code change by
setting OMS360_DB_DIAGNOSTICS=false.
"""

import hashlib
import os
import platform

from app.core.logging_config import get_logger

logger = get_logger("oms360.db.diagnostics")

FINGERPRINT_SALT = b"oms360-db-diag-v1:"
DB_ENV_KEYS = ("OMS360_DB_HOST", "OMS360_DB_PORT", "OMS360_DB_USER",
               "OMS360_DB_PASSWORD", "OMS360_DB_NAME", "OMS360_DB_SSL")


def password_fingerprint(password: str) -> str:
    return hashlib.sha256(FINGERPRINT_SALT + password.encode("utf-8")).hexdigest()[:12]


def config_source(key: str, pre_dotenv_keys, environ=None) -> str:
    environ = os.environ if environ is None else environ
    if key in pre_dotenv_keys:
        return "process environment"
    if key in environ:
        return ".env file"
    return "code default"


def build_db_diagnostic(engine_url, connect_args: dict, pre_dotenv_keys, environ=None) -> dict:
    """Pure function (no I/O) so it can be unit-tested. Returns only
    non-secret values."""
    import pymysql
    import sqlalchemy

    password = engine_url.password or ""
    ssl = (connect_args or {}).get("ssl") or {}
    return {
        "host": engine_url.host,
        "port": engine_url.port,
        "user": engine_url.username,
        "database": engine_url.database,
        "driver": engine_url.drivername,
        "ssl_enabled": bool(ssl),
        "ssl_ca": ssl.get("ca") if ssl else None,
        "password_length": len(password),
        "password_fingerprint": password_fingerprint(password) if password else None,
        "password_is_ascii": password.isascii(),
        "sources": {k: config_source(k, pre_dotenv_keys, environ) for k in DB_ENV_KEYS},
        "python": platform.python_version(),
        "sqlalchemy": sqlalchemy.__version__,
        "pymysql": pymysql.__version__,
        "pid": os.getpid(),
    }


def log_db_diagnostic() -> None:
    """Called once at startup. Never raises - a diagnostic must not be able
    to stop the application."""
    if os.getenv("OMS360_DB_DIAGNOSTICS", "true").strip().lower() == "false":
        return
    try:
        from app import config, database
        info = build_db_diagnostic(database.engine.url, database._connect_args,
                                   config.PRE_DOTENV_ENV_KEYS)
        logger.info("DB_DIAGNOSTIC " + " ".join(
            f"{k}={v}" for k, v in info.items() if k != "sources")
            + " sources=" + ",".join(f"{k}:{v}" for k, v in info["sources"].items()))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"DB_DIAGNOSTIC unavailable: {type(exc).__name__}")
