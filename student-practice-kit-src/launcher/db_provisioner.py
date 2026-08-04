"""
launcher/db_provisioner.py - starts a private, embedded MySQL-compatible
database for the Student Practice Edition, with zero changes to
app/config.py or app/database.py.

How this stays "do not modify business logic": app/config.py already
reads DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME from environment
variables (OMS360_DB_HOST etc.) with sensible defaults - that's the
existing, unmodified 12-factor design. This module's only interaction
with the business logic is setting those same environment variables
*before* `app.main` (and therefore `app.database`, which builds the
SQLAlchemy engine from `settings.DATABASE_URL` at import time) is
imported - see launcher/main.py. Nothing here imports, edits, or
special-cases any file under app/ or ai/.

What "embedded" means here concretely: the official MySQL Community
Server Windows ZIP ("noinstall") distribution is downloaded and staged
into resources/mysql-portable/ once, at BUILD time, by build/build.bat
(see that script - the exact version and its official SHA256 checksum are
pinned there, verified before use). PyInstaller then bundles that folder
as a data resource inside the single onefile .exe. At first run, this
module copies it out to a persistent per-user folder (PyInstaller onefile
mode re-extracts bundled data to a fresh temp directory on every launch,
which would lose the database between sessions if used directly),
initializes a fresh MySQL data directory there, applies the project's own
unmodified `oms360_schema.sql` + `migrations/002_add_audit_trail.sql` +
`migrations/003_add_inventory_ledger.sql` (bundled the same way, byte-for-
byte, sourced from the real repository root - not retyped or altered),
and starts `mysqld.exe` bound to 127.0.0.1 only, on a port unlikely to
collide with any MySQL the student may already have installed.

Untested from this build environment: everything in this module is
Windows-specific (mysqld.exe, %LOCALAPPDATA%) and depends on the actual
portable MySQL binary that only exists once build.bat downloads it on a
real Windows machine - it cannot be executed or verified from the Linux
environment this was authored in. See build/README.md,
"What to verify after your first build" for the manual checklist to run
through once, on Windows, before handing this out to students.
"""

import atexit
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

APP_DATA_DIRNAME = "ZelQA"
APP_SUBDIRNAME = "OMS360PracticeKit"
MYSQL_SUBDIR = "mysql"
LOCAL_DB_PORT = 33071          # deliberately not 3306, to avoid colliding
                                # with any MySQL the student already has
LOCAL_DB_PORT_SCAN_RANGE = 50  # if 33071 is busy (e.g. a leftover mysqld.exe
                                # from a previous run that wasn't closed
                                # normally), automatically try 33072, 33073,
                                # ... instead of failing with a fatal dialog
LOCAL_DB_USER = "root"
LOCAL_DB_PASSWORD = ""         # root initialized with --initialize-insecure;
                                # this instance is 127.0.0.1-only, per-user
LOCAL_DB_NAME = "oms360_db"
STARTUP_TIMEOUT_SECONDS = 45

_active_port = None  # resolved lazily by get_active_port() - the port this
                      # run actually ends up using, which may differ from
                      # LOCAL_DB_PORT if that one was already taken


class ProvisioningError(RuntimeError):
    pass


def _bundle_resource_dir() -> Path:
    """Where bundled resources (mysql-portable/, sql/) live: PyInstaller's
    onefile extraction dir when frozen, or the source tree's resources/
    folder when running unfrozen (`python -m launcher.main`, for dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "resources"
    return Path(__file__).resolve().parent.parent / "build" / "resources"


def _persistent_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return base / APP_DATA_DIRNAME / APP_SUBDIRNAME


def _mysql_persistent_dir() -> Path:
    return _persistent_root() / MYSQL_SUBDIR


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _find_available_port(preferred: int, max_attempts: int = LOCAL_DB_PORT_SCAN_RANGE) -> int:
    """Return `preferred` if it's free. Otherwise scan upward for the next
    free port. This is what lets a fresh launch succeed even when a
    previous run's mysqld.exe is still holding `preferred` (e.g. the app
    was closed via Task Manager / a build was aborted instead of using the
    normal Stop button) - instead of failing with a "port already in use"
    dialog, it just runs the local database on a different port."""
    for candidate in range(preferred, preferred + max_attempts):
        if _is_port_free(candidate):
            return candidate
    raise ProvisioningError(
        f"Could not find a free port for the local database - every port "
        f"from {preferred} to {preferred + max_attempts - 1} is in use. "
        f"Please restart your computer and try again, or contact ZelQA "
        f"Technologies."
    )


def get_active_port() -> int:
    """The port this run is actually using. Resolved once, lazily, the
    first time it's needed, and cached for the rest of the process
    lifetime so every caller (schema application, health check, the
    running server, env_overrides()) agrees on the same port."""
    global _active_port
    if _active_port is None:
        _active_port = _find_available_port(LOCAL_DB_PORT)
    return _active_port


def _mysqld_path(mysql_dir: Path) -> Path:
    return mysql_dir / "bin" / "mysqld.exe"


def _mysqld_log_path(mysql_dir: Path) -> Path:
    return mysql_dir / "mysqld_launch.log"


def _tail_mysqld_log(mysql_dir: Path, max_chars: int = 1500) -> str:
    """Best-effort excerpt of mysqld's own console output, so a startup
    failure dialog shows the REAL reason (e.g. a corrupted data directory
    after a hard taskkill, a permissions problem, disk full) instead of
    just 'timed out' - which is the symptom, not the cause."""
    log_path = _mysqld_log_path(mysql_dir)
    if not log_path.exists():
        return "(mysqld produced no log output)"
    try:
        data = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(could not read mysqld's log: {exc})"
    if not data.strip():
        return "(mysqld's log is empty)"
    return f"Local database engine's own output:\n{data[-max_chars:]}"


def _mysql_client_path(mysql_dir: Path) -> Path:
    return mysql_dir / "bin" / "mysql.exe"


def is_provisioned() -> bool:
    marker = _mysql_persistent_dir() / "data" / ".oms360_provisioned"
    return marker.exists()


def provision(on_progress=None) -> None:
    """One-time setup: copy the bundled portable MySQL engine to a
    persistent folder, initialize a fresh data directory, apply the
    project's schema + migrations. Safe to call every launch - it's a
    no-op if `is_provisioned()` is already True."""
    def report(msg):
        if on_progress:
            on_progress(msg)

    if is_provisioned():
        report("Local database already provisioned.")
        return

    bundle_dir = _bundle_resource_dir()
    bundled_mysql = bundle_dir / "mysql-portable"
    sql_dir = bundle_dir / "sql"

    if not bundled_mysql.exists():
        raise ProvisioningError(
            "This build does not have an embedded database engine bundled "
            "(resources/mysql-portable/ is missing). Re-run build.bat, "
            "which stages it automatically - see build/README.md."
        )

    persistent_mysql = _mysql_persistent_dir()
    persistent_mysql.mkdir(parents=True, exist_ok=True)

    report("Preparing the local database engine (first run only)...")
    dest_bin = persistent_mysql / "bin"
    if not dest_bin.exists():
        shutil.copytree(bundled_mysql, persistent_mysql, dirs_exist_ok=True)

    data_dir = persistent_mysql / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    report("Initializing the database (first run only, ~10-20s)...")
    init_result = subprocess.run(
        [
            str(_mysqld_path(persistent_mysql)),
            f"--datadir={data_dir}",
            "--initialize-insecure",
        ],
        capture_output=True, text=True, timeout=120,
    )
    if init_result.returncode != 0:
        raise ProvisioningError(
            f"Database initialization failed:\n{init_result.stderr[-2000:]}"
        )

    report("Starting the local database to apply the schema...")
    proc = start_mysqld(persistent_mysql, data_dir)
    try:
        _wait_for_mysqld(persistent_mysql, proc)

        report("Applying oms360_schema.sql...")
        _apply_sql_file(persistent_mysql, sql_dir / "oms360_schema.sql", create_database=True)

        for migration in ("002_add_audit_trail.sql", "003_add_inventory_ledger.sql"):
            path = sql_dir / migration
            if path.exists():
                report(f"Applying {migration}...")
                _apply_sql_file(persistent_mysql, path, create_database=False)
    finally:
        stop_mysqld(proc)

    (data_dir / ".oms360_provisioned").write_text("ok", encoding="utf-8")
    report("Local database ready.")


def _apply_sql_file(mysql_dir: Path, sql_path: Path, create_database: bool) -> None:
    if not sql_path.exists():
        raise ProvisioningError(f"Expected bundled SQL file not found: {sql_path.name}")

    client = _mysql_client_path(mysql_dir)
    args = [str(client), "-h", "127.0.0.1", "-P", str(get_active_port()), "-u", LOCAL_DB_USER]

    if create_database:
        create_db = subprocess.run(
            args + ["-e", f"CREATE DATABASE IF NOT EXISTS {LOCAL_DB_NAME};"],
            capture_output=True, text=True, timeout=30,
        )
        if create_db.returncode != 0:
            raise ProvisioningError(f"Could not create database: {create_db.stderr}")

    with sql_path.open("rb") as sql_stream:
        result = subprocess.run(
            args + [LOCAL_DB_NAME],
            stdin=sql_stream, capture_output=True, text=True, timeout=120,
        )
    if result.returncode != 0:
        raise ProvisioningError(f"Applying {sql_path.name} failed:\n{result.stderr[-2000:]}")


def start_mysqld(mysql_dir: Path = None, data_dir: Path = None) -> subprocess.Popen:
    mysql_dir = mysql_dir or _mysql_persistent_dir()
    data_dir = data_dir or (mysql_dir / "data")

    # Picks LOCAL_DB_PORT (33071) if free, or the next free port after it
    # if not - so a leftover mysqld.exe from a previous run never blocks a
    # fresh launch with a fatal "port already in use" dialog.
    port = get_active_port()

    creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    # Truncated (mode "w") each start, not appended - the log should always
    # reflect only the most recent launch attempt, so a failure dialog's
    # excerpt is never stale output from a previous, unrelated run.
    log_file = open(_mysqld_log_path(mysql_dir), "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [
            str(_mysqld_path(mysql_dir)),
            f"--datadir={data_dir}",
            f"--port={port}",
            "--bind-address=127.0.0.1",
            "--skip-networking=0",
            "--console",
        ],
        stdout=log_file, stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    # Belt-and-suspenders cleanup: if the app exits normally (including via
    # an unhandled exception) without going through stop_mysqld() itself -
    # e.g. main.py's own on_stop() path is skipped - this still shuts the
    # server down instead of leaving it orphaned on `port`. This does not
    # fire on a hard kill (Task Manager "End task", taskkill /F), which is
    # exactly why get_active_port() above exists as a second line of
    # defense.
    atexit.register(stop_mysqld, proc)
    atexit.register(log_file.close)
    return proc


def _wait_for_mysqld(mysql_dir: Path, proc: subprocess.Popen = None) -> None:
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    last_error = None
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            # mysqld already exited - waiting out the rest of the timeout
            # would just delay showing the real problem. Its own log (see
            # start_mysqld) has the actual reason.
            raise ProvisioningError(
                f"The local database engine exited immediately "
                f"(exit code {proc.returncode}) instead of starting.\n\n"
                f"{_tail_mysqld_log(mysql_dir)}"
            )
        try:
            import pymysql
            conn = pymysql.connect(
                host="127.0.0.1", port=get_active_port(),
                user=LOCAL_DB_USER, password=LOCAL_DB_PASSWORD,
                connect_timeout=2,
            )
            conn.close()
            return
        except Exception as exc:  # noqa: BLE001 - genuinely any connect failure means "not ready yet"
            last_error = exc
            time.sleep(1)
    raise ProvisioningError(
        f"Local database did not become ready within {STARTUP_TIMEOUT_SECONDS}s. "
        f"Last error: {last_error}\n\n{_tail_mysqld_log(mysql_dir)}"
    )


def stop_mysqld(proc: subprocess.Popen) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=15)
    except Exception:
        proc.kill()


def env_overrides() -> dict:
    """The exact environment variable names app/config.py already reads
    (see ApplicationSettings) - this is configuration, not a code change."""
    return {
        "OMS360_DB_HOST": "127.0.0.1",
        "OMS360_DB_PORT": str(get_active_port()),
        "OMS360_DB_USER": LOCAL_DB_USER,
        "OMS360_DB_PASSWORD": LOCAL_DB_PASSWORD,
        "OMS360_DB_NAME": LOCAL_DB_NAME,
        "OMS360_KAFKA_ENABLED": "false",
        "OMS360_APP_ENV": "evaluation",
        "OMS360_DOCKER_MODE": "false",
        "OMS360_BUILD_VERSION": "student-practice-edition",
    }
