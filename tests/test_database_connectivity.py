"""
Production database connectivity regression tests (2026-11-22).

Background: after the TiDB password was reset, Render logged
    (1045, "Access denied for user '<prefix>.root'@'<render-ip>' (using password: YES)")
app/config.py built the connection URL by plain string formatting, so a
password containing URL-special characters (%xx, @, #, ...) or a stray
trailing space / CR / LF from a dashboard paste reached TiDB altered.
The fix builds DATABASE_URL with sqlalchemy URL.create() and trims
environment values.

Also covers: TLS connect args, honest /health database status, and the
inventory API (list-all without truncation, create, update, stock rule)
through the real FastAPI routes on an in-memory SQLite database.

Self-contained: no MySQL/TiDB, no Kafka, no email. All passwords below
are fake test values.
Run:  pytest tests/test_database_connectivity.py -v
"""

import json
import os
import subprocess
import sys

import certifi
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.config import ApplicationSettings, _env, settings
from app.database import Base, build_connect_args, get_db
from app.main import app

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIDB_HOST = "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"
TIDB_USER = "AbCdEf123456.root"


def _settings(password, user=TIDB_USER, host=TIDB_HOST, port=4000, name="oms360_db"):
    s = ApplicationSettings()
    s.DB_USER, s.DB_PASSWORD, s.DB_HOST, s.DB_PORT, s.DB_NAME = user, password, host, port, name
    return s


def _pymysql_kwargs(url):
    """Exactly what SQLAlchemy would hand to pymysql.connect() - no network."""
    engine = create_engine(url)
    try:
        _args, kwargs = engine.dialect.create_connect_args(engine.url)
        return kwargs
    finally:
        engine.dispose()


# --------------------------------------------------------------------------
# 1. Password is passed through exactly, whatever it contains
# --------------------------------------------------------------------------
PASSWORDS = [
    "Abc123xyz",                 # plain alphanumeric (TiDB-generated style)
    "ab%40cd",                   # % + hex - old code decoded this to "ab@cd"
    "p%ss%",                     # bare %
    "p@ss@word",                 # @ - old code split host at the first @
    "pa#ss",                     # #
    "pass word",                 # inner space
    "a:b/c?d=e&f",               # : / ? = &
    "!$^*()[]{}|;'\",.<>~`+-_",  # assorted punctuation
    "pässwörd€",                 # non-ASCII
]


@pytest.mark.parametrize("password", PASSWORDS)
def test_password_reaches_driver_unchanged(password):
    kwargs = _pymysql_kwargs(_settings(password).DATABASE_URL)
    assert kwargs["password"] == password
    assert kwargs["user"] == TIDB_USER
    assert kwargs["host"] == TIDB_HOST
    assert kwargs["port"] == 4000
    assert kwargs["database"] == "oms360_db"


@pytest.mark.parametrize("password", PASSWORDS)
def test_rendered_url_round_trips(password):
    """Rendering then re-parsing the URL must give back the same parts."""
    url = _settings(password).DATABASE_URL
    reparsed = make_url(url.render_as_string(hide_password=False))
    assert (reparsed.password, reparsed.username, reparsed.host, reparsed.port, reparsed.database) == \
           (password, TIDB_USER, TIDB_HOST, 4000, "oms360_db")


def test_old_string_url_would_have_corrupted_passwords():
    """Documents the defect: the previous f-string URL altered these."""
    def old_url(pw):
        return f"mysql+pymysql://{TIDB_USER}:{pw}@{TIDB_HOST}:4000/oms360_db"
    assert make_url(old_url("ab%40cd")).password == "ab@cd"          # silently changed
    assert make_url(old_url("p@ss@word")).host != TIDB_HOST          # host corrupted


def test_driver_and_tidb_username_prefix_preserved():
    url = _settings("x").DATABASE_URL
    assert url.drivername == "mysql+pymysql"
    assert url.username == TIDB_USER and "." in url.username


def test_str_of_url_never_shows_the_password():
    secret = "S3cret%40Value#1"
    url = _settings(secret).DATABASE_URL
    assert secret not in str(url)
    assert secret not in repr(url)
    assert "***" in str(url)


# --------------------------------------------------------------------------
# 2. Environment values: whitespace trimmed, names unchanged
# --------------------------------------------------------------------------
@pytest.mark.parametrize("raw, expected", [
    ("Abc123xyz ", "Abc123xyz"),
    (" Abc123xyz", "Abc123xyz"),
    ("Abc123xyz\r\n", "Abc123xyz"),
    ("\tAbc 123\t", "Abc 123"),       # inner space kept
])
def test_env_values_are_trimmed(monkeypatch, raw, expected):
    monkeypatch.setenv("OMS360_TEST_VALUE", raw)
    assert _env("OMS360_TEST_VALUE", "default") == expected


def test_env_default_used_when_unset(monkeypatch):
    monkeypatch.delenv("OMS360_TEST_VALUE", raising=False)
    assert _env("OMS360_TEST_VALUE", "default") == "default"


def test_settings_read_the_existing_render_variable_names():
    """Fresh interpreter, so the real module-level settings are built from
    the env exactly as on Render. Values are fake."""
    env = dict(os.environ)
    env.update({
        "OMS360_DB_HOST": f" {TIDB_HOST} ",
        "OMS360_DB_PORT": "4000\r\n",
        "OMS360_DB_USER": f"{TIDB_USER} ",
        "OMS360_DB_PASSWORD": "Fake%40Pass word#9 \r\n",
        "OMS360_DB_NAME": "oms360_db ",
    })
    code = (
        "import json; from app.config import settings as s; u = s.DATABASE_URL; "
        "print(json.dumps([u.username, u.password, u.host, u.port, u.database]))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, env=env,
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out.strip().splitlines()[-1]) == \
           [TIDB_USER, "Fake%40Pass word#9", TIDB_HOST, 4000, "oms360_db"]


def test_engine_still_built_from_settings_database_url():
    from app import database
    assert database.engine.url.render_as_string(hide_password=False) == \
           settings.DATABASE_URL.render_as_string(hide_password=False)


# --------------------------------------------------------------------------
# 3. TLS
# --------------------------------------------------------------------------
@pytest.mark.parametrize("value", ["true", "TRUE", "True", " true ", "true\r\n"])
def test_ssl_enabled_uses_certifi_ca(monkeypatch, value):
    monkeypatch.setenv("OMS360_DB_SSL", value)
    args = build_connect_args()
    assert args == {"ssl": {"ca": certifi.where()}}
    assert os.path.isfile(args["ssl"]["ca"])


@pytest.mark.parametrize("value", ["false", "", "no", "0"])
def test_ssl_disabled_values(monkeypatch, value):
    monkeypatch.setenv("OMS360_DB_SSL", value)
    assert build_connect_args() == {}


def test_ssl_unset_is_disabled(monkeypatch):
    monkeypatch.delenv("OMS360_DB_SSL", raising=False)
    assert build_connect_args() == {}


# --------------------------------------------------------------------------
# 4. /health and inventory API through the real routes (SQLite)
# --------------------------------------------------------------------------
@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session, monkeypatch):
    monkeypatch.setattr(settings, "KAFKA_ENABLED", False)
    monkeypatch.setitem(settings.FEATURE_FLAGS, "notifications_enabled", False)  # never email

    def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_db, None)


def test_health_reports_database_up_when_reachable(client):
    body = client.get("/health").json()
    assert body["dependencies"]["application"] == "UP"
    assert body["dependencies"]["database"].startswith("UP")


def test_health_reports_database_down_without_leaking_error(monkeypatch, db_session):
    class BrokenSession:
        def execute(self, *a, **k):
            raise RuntimeError("(1045, \"Access denied for user 'AbCdEf123456.root'@'1.2.3.4'\")")
        def close(self):
            pass

    monkeypatch.setattr(settings, "KAFKA_ENABLED", False)
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        resp = TestClient(app, raise_server_exceptions=False).get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)
    body = resp.json()
    assert body["dependencies"]["database"] == "DOWN"
    assert body["status"] != "HEALTHY"
    raw = resp.text
    assert "Access denied" not in raw and "AbCdEf123456" not in raw and "1.2.3.4" not in raw


def _seed(db, n):
    for i in range(n):
        stock = [0, 2, 4, 5, 12][i % 5]
        db.add(models.Inventory(item_id=f"ITEM-T{i:03d}", item_name=f"Item {i}", price=10,
                                total_stock=max(stock, 1), remaining_stock=stock, used_stock=0,
                                status="ACTIVE"))
    db.commit()


@pytest.mark.parametrize("n", [12, 25, 120])
def test_list_inventory_returns_every_row_in_order(client, db_session, n):
    _seed(db_session, n)
    rows = client.get("/api/v1/inventory").json()
    assert len(rows) == n
    assert [r["item_id"] for r in rows] == sorted(r["item_id"] for r in rows)


def test_low_and_out_of_stock_endpoints_follow_rule(client, db_session):
    _seed(db_session, 10)   # stocks cycle 0,2,4,5,12
    low = {r["remaining_stock"] for r in client.get("/api/v1/inventory/low-stock").json()}
    out = {r["remaining_stock"] for r in client.get("/api/v1/inventory/out-of-stock").json()}
    assert low == {2, 4}
    assert out == {0}


@pytest.mark.parametrize("stock, expected", [
    (0, "OUT_OF_STOCK"), (1, "LOW_STOCK"), (4, "LOW_STOCK"), (5, "ACTIVE"), (12, "ACTIVE"),
])
def test_create_item_applies_stock_rule(client, stock, expected):
    resp = client.post("/api/v1/inventory", json={"item_name": "ragi jowari dosa", "price": 250,
                                                   "total_stock": stock, "status": "ACTIVE"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["item_id"].startswith("ITEM-")
    assert (body["remaining_stock"], body["status"]) == (stock, expected)
    listed = [r["item_id"] for r in client.get("/api/v1/inventory").json()]
    assert body["item_id"] in listed


def test_update_item_stock_reclassifies(client):
    item_id = client.post("/api/v1/inventory", json={"item_name": "Veg Idly", "price": 90,
                                                     "total_stock": 20}).json()["item_id"]
    for stock, expected in [(3, "LOW_STOCK"), (0, "OUT_OF_STOCK"), (5, "ACTIVE")]:
        resp = client.put(f"/api/v1/inventory/{item_id}", json={"stock": stock})
        assert resp.status_code == 200, resp.text
        assert (resp.json()["remaining_stock"], resp.json()["status"]) == (stock, expected)


def test_update_unknown_item_returns_404(client):
    assert client.put("/api/v1/inventory/ITEM-NOPE", json={"price": 10}).status_code == 404


def test_inventory_has_no_delete_endpoint(client, db_session):
    """Documents current behaviour: items are deactivated (status INACTIVE),
    never deleted, so DELETE is not routed."""
    _seed(db_session, 1)
    assert client.delete("/api/v1/inventory/ITEM-T000").status_code in (404, 405)
    assert db_session.get(models.Inventory, "ITEM-T000") is not None


def test_gitignore_excludes_local_tidb_admin_tools():
    with open(os.path.join(REPO_ROOT, ".gitignore"), encoding="utf-8") as fh:
        lines = {ln.strip() for ln in fh}
    assert {".env", "TIDB.bat", "TIDB.ps1"} <= lines
