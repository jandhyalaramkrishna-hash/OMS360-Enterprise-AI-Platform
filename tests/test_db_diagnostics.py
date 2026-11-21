"""
Tests for the TEMPORARY database-configuration diagnostic (2026-11-22).

Core guarantee: the diagnostic NEVER outputs the password, in any form other
than its length and a salted, truncated SHA-256 fingerprint. All passwords
here are fake.
Run:  pytest tests/test_db_diagnostics.py -v
"""

import hashlib
import json
import logging
import os
import subprocess
import sys

import certifi
import pytest

from app.config import ApplicationSettings
from app.core import db_diagnostics as diag

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"
USER = "AbCdEf123456.root"
SECRETS = ["Abc123xyz9876543", "ab%40cd", "p@ss@word", "pa#ss", "pass word", "x$y`z^%%!", "pässwörd"]


def _url(password):
    s = ApplicationSettings()
    s.DB_USER, s.DB_PASSWORD, s.DB_HOST, s.DB_PORT, s.DB_NAME = USER, password, HOST, 4000, "oms360_db"
    return s.DATABASE_URL


def test_fingerprint_formula_is_fixed_and_documented():
    pw = "Abc123xyz9876543"
    expected = hashlib.sha256(b"oms360-db-diag-v1:" + pw.encode("utf-8")).hexdigest()[:12]
    assert diag.password_fingerprint(pw) == expected
    assert len(expected) == 12


def test_fingerprint_differs_for_different_passwords():
    assert diag.password_fingerprint("Abc123xyz9876543") != diag.password_fingerprint("Abc123xyz9876544")


@pytest.mark.parametrize("secret", SECRETS)
def test_report_contains_connection_facts_but_never_the_password(secret):
    info = diag.build_db_diagnostic(_url(secret), {"ssl": {"ca": certifi.where()}},
                                    pre_dotenv_keys=set(diag.DB_ENV_KEYS), environ={})
    assert (info["host"], info["port"], info["user"], info["database"]) == (HOST, 4000, USER, "oms360_db")
    assert info["ssl_enabled"] is True and info["ssl_ca"] == certifi.where()
    assert info["password_length"] == len(secret)
    assert info["password_fingerprint"] == diag.password_fingerprint(secret)
    assert info["password_is_ascii"] == secret.isascii()
    assert secret not in json.dumps(info, ensure_ascii=False)


def test_ssl_disabled_reported():
    info = diag.build_db_diagnostic(_url("x"), {}, pre_dotenv_keys=set(), environ={})
    assert info["ssl_enabled"] is False and info["ssl_ca"] is None


def test_empty_password_has_no_fingerprint():
    info = diag.build_db_diagnostic(_url(""), {}, pre_dotenv_keys=set(), environ={})
    assert info["password_length"] == 0 and info["password_fingerprint"] is None


def test_config_sources():
    pre = {"OMS360_DB_PASSWORD"}
    env = {"OMS360_DB_PASSWORD": "x", "OMS360_DB_HOST": "h"}
    assert diag.config_source("OMS360_DB_PASSWORD", pre, env) == "process environment"
    assert diag.config_source("OMS360_DB_HOST", pre, env) == ".env file"
    assert diag.config_source("OMS360_DB_NAME", pre, env) == "code default"


@pytest.mark.parametrize("secret", SECRETS)
def test_startup_log_line_never_contains_the_password(secret, caplog, monkeypatch):
    from app import config, database
    monkeypatch.setattr(database.engine, "url", _url(secret))
    monkeypatch.setattr(config, "PRE_DOTENV_ENV_KEYS", frozenset(diag.DB_ENV_KEYS))
    diag.logger.propagate = True
    with caplog.at_level(logging.INFO, logger="oms360.db.diagnostics"):
        diag.log_db_diagnostic()
    text = caplog.text
    assert "DB_DIAGNOSTIC" in text
    assert secret not in text
    assert f"password_fingerprint={diag.password_fingerprint(secret)}" in text
    assert f"password_length={len(secret)}" in text


def test_can_be_disabled(caplog, monkeypatch):
    monkeypatch.setenv("OMS360_DB_DIAGNOSTICS", "false")
    diag.logger.propagate = True
    with caplog.at_level(logging.INFO, logger="oms360.db.diagnostics"):
        diag.log_db_diagnostic()
    assert "DB_DIAGNOSTIC" not in caplog.text


def test_full_startup_in_fresh_process_reports_render_style_environment():
    """Simulates Render: values set in the real process environment, with
    surrounding whitespace, and app.main imported exactly as uvicorn does."""
    secret = "Fake9Pass8Word7X"
    env = dict(os.environ)
    env.update({"OMS360_DB_HOST": f" {HOST} ", "OMS360_DB_PORT": "4000", "OMS360_DB_USER": USER,
                "OMS360_DB_PASSWORD": secret + "\r\n", "OMS360_DB_NAME": "oms360_db",
                "OMS360_DB_SSL": "true", "OMS360_KAFKA_ENABLED": "false"})
    out = subprocess.run([sys.executable, "-c", "import app.main"], cwd=REPO_ROOT, env=env,
                         capture_output=True, text=True, timeout=120)
    logs = out.stdout + out.stderr
    line = next(ln for ln in logs.splitlines() if "DB_DIAGNOSTIC" in ln)
    assert secret not in logs
    assert f"host={HOST}" in line and "port=4000" in line and f"user={USER}" in line
    assert "database=oms360_db" in line and "ssl_enabled=True" in line
    assert "password_length=16" in line                                  # trimmed
    assert f"password_fingerprint={diag.password_fingerprint(secret)}" in line
    assert "OMS360_DB_PASSWORD:process environment" in line


def test_diagnostic_failure_never_stops_startup(monkeypatch):
    from app import database
    monkeypatch.setattr(database, "engine", None)        # force an internal error
    diag.log_db_diagnostic()                              # must not raise
