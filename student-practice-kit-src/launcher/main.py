"""
launcher/main.py - entry point for OMS360 Enterprise AI Platform.exe (the
Student Practice Edition).

Startup sequence:
  0. Show a branded splash window immediately (launcher/splash.py) - a
     student should see something the instant they double-click, not a
     blank few seconds while Python starts up.
  1. License gate (licensing/) - first run: prompt for a key (the splash
     is closed first, since activation_ui.py opens its own Tk root); every
     run: reject if expired. Nothing past this point runs without a valid,
     non-expired activation.
  2. Provision + start the embedded local database (db_provisioner.py) -
     zero changes to app/config.py or app/database.py, pure environment
     configuration those files already support. A fresh splash window
     shows progress at each step via the same on_progress callback
     db_provisioner.provision() already accepted.
  3. Import the REAL, unmodified `app.main:app` FastAPI application and
     run it in-process via uvicorn, in a background thread.
  4. Close the splash, open the student's browser to the running app.
  5. Show a small status window (with an About button) until the student
     stops it or the evaluation expires.

This file contains NO OMS360 business logic of its own - every route,
service, model, and schema it ends up serving is exactly what `app/`
already defines. Its own responsibilities are the license gate, the
branded splash/status/about UI wrapped around that, and turning the
embedded database on before `app.main` is imported.
"""

import os
import sys
import threading
import time

# A --windowed/--noconsole PyInstaller build (this one) has no console, so
# sys.stdout and sys.stderr are None, not just empty/quiet streams. Any
# library that calls .write()/.flush()/.isatty() on them - uvicorn's own
# logging setup does exactly this - crashes with an error that gives no
# hint the real problem is "there is no console." Redirecting both to
# os.devnull as early as possible (before anything else in this process
# might touch them) makes them behave like real, harmless, always-writable
# streams instead of None. 2026-07-31 fix: this is what was causing
# "ValueError: Unable to configure formatter 'default'" from inside
# uvicorn.Config() on a student's real Windows machine - see
# _run_app_and_wait_ready()'s log_config=None below for the other half of
# this fix.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# --- 0. Splash (shown immediately on double-click, before anything else) ---

from licensing import keys  # noqa: E402
from licensing.gate import LicenseGate  # noqa: E402


def _run_license_gate(splash):
    splash.set_status("Checking license...")
    gate = LicenseGate()
    status = gate.current_status()

    if status.activated and status.expired:
        splash.close()
        from launcher.activation_ui import show_evaluation_expired
        show_evaluation_expired()
        sys.exit(1)

    if not status.activated:
        # activation_ui opens its own Tk root - close the splash first so
        # only one Tkinter root exists on screen at a time.
        splash.close()
        from launcher.activation_ui import prompt_for_license_key
        status = prompt_for_license_key(gate)
        if status is None:
            sys.exit(0)  # student closed the activation dialog

    return status


# --- 1. Embedded database ----------------------------------------------------

def _provision_and_start_database(splash):
    from launcher import db_provisioner
    from launcher.activation_ui import show_fatal_error

    try:
        db_provisioner.provision(on_progress=splash.set_status)
    except db_provisioner.ProvisioningError as exc:
        splash.close()
        show_fatal_error(
            "Database setup failed",
            "The embedded local database could not be prepared.\n\n"
            f"{exc}\n\n"
            "Please contact ZelQA Technologies with this message.",
        )
        sys.exit(1)

    os.environ.update(db_provisioner.env_overrides())

    splash.set_status("Starting local database...")
    try:
        db_proc = db_provisioner.start_mysqld()
        db_provisioner._wait_for_mysqld(db_provisioner._mysql_persistent_dir(), db_proc)
    except db_provisioner.ProvisioningError as exc:
        splash.close()
        show_fatal_error(
            "Database startup failed",
            f"{exc}\n\nPlease contact ZelQA Technologies with this message.",
        )
        sys.exit(1)

    return db_proc


# --- 2 & 3. Run the real app, in-process, and open the browser --------------

def _run_app_and_wait_ready(host: str, port: int, splash):
    """Imports app.main AFTER env vars are set (required - app/config.py
    and app/database.py both read settings at import time), starts it via
    uvicorn on a background thread, and blocks until /health responds."""
    import uvicorn

    splash.set_status(f"Starting {keys.BRAND_NAME}...")
    from app.main import app  # the real, unmodified FastAPI app

    # log_config=None: skip uvicorn's own logging setup entirely - there's
    # no console for it to log to anyway (windowed build), and its default
    # setup is exactly what raised "Unable to configure formatter 'default'"
    # (see the sys.stdout/sys.stderr guard near the top of this file for
    # the underlying reason and the rest of this fix).
    config = uvicorn.Config(app, host=host, port=port, log_level="warning", log_config=None)
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    import httpx
    base_url = f"http://{host}:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{base_url}/health", timeout=2)
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
        splash.set_status("Waiting for application to become ready...")

    return server, thread, base_url


def main():
    from launcher.splash import show_splash

    splash = show_splash(f"Starting {keys.BRAND_NAME}...")
    status = _run_license_gate(splash)  # may close() and reopen its own root

    # License gate may have closed the first splash to show the activation
    # dialog (see above) - start a fresh one for the provisioning phase.
    splash = show_splash("Preparing your evaluation environment...")
    db_proc = _provision_and_start_database(splash)

    server, uvicorn_thread, base_url = _run_app_and_wait_ready(host="127.0.0.1", port=8000, splash=splash)
    splash.close()

    import webbrowser
    webbrowser.open(f"{base_url}/docs")
    webbrowser.open(f"{base_url}/dashboard/operations")

    from launcher import db_provisioner
    from licensing.gate import LicenseGate
    from launcher.status_window import run_status_window

    def on_stop():
        server.should_exit = True
        uvicorn_thread.join(timeout=10)
        db_provisioner.stop_mysqld(db_proc)

    def on_check_expired():
        return LicenseGate().current_status()

    run_status_window(status, base_url, on_stop=on_stop, on_check_expired=on_check_expired)


if __name__ == "__main__":
    main()
