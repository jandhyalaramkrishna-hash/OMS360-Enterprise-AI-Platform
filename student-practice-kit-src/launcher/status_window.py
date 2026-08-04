"""
launcher/status_window.py - the small always-visible window shown while
the Student Practice Edition is running (this app is built --windowed, so
there is no console - this window is how a student knows it's alive, sees
where to open it, and how to stop it).
"""

import threading
import time
import tkinter as tk
import webbrowser

from shared_ui.about_dialog import show_about_dialog
from shared_ui.icon import PLATFORM_ICON_NAME, set_window_icon
from licensing import keys
from licensing.activation_store import ActivationStatus

_CHECK_INTERVAL_MS = 30_000  # re-check expiry every 30s while running


def _format_remaining(seconds: float) -> str:
    if seconds is None:
        return "unknown"
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h remaining"
    if hours > 0:
        return f"{hours}h {minutes}m remaining"
    return f"{minutes}m remaining"


def _format_days_remaining(seconds: float) -> str:
    """The spec's Student Edition surface asks for a plain 'Days Remaining'
    figure distinct from the more detailed d/h/m readout above. Rounds up
    to the nearest whole day so a student with, say, 40 minutes left still
    sees "Less than 1 day" rather than a misleading "0 days"."""
    if seconds is None:
        return "unknown"
    seconds = max(0, int(seconds))
    if seconds == 0:
        return "0 days"
    days = -(-seconds // 86400)  # ceiling division
    if days <= 1 and seconds < 86400:
        return "Less than 1 day"
    return f"{days} day{'s' if days != 1 else ''}"


def run_status_window(status: ActivationStatus, base_url: str, on_stop, on_check_expired):
    """Blocks (mainloop) until the student clicks Stop, closes the window,
    or the periodic expiry check fires. `on_stop` is called exactly once,
    on the way out, to shut down uvicorn/mysqld. `on_check_expired` is
    called on the periodic timer and should return the latest
    ActivationStatus (re-reads the activation store)."""

    root = tk.Tk()
    root.title(f"{keys.BRAND_NAME} - {keys.BRAND_EDITION}")
    root.resizable(False, False)
    root.geometry("480x360")
    set_window_icon(root, PLATFORM_ICON_NAME)

    stopped = {"done": False}

    def do_stop():
        if stopped["done"]:
            return
        stopped["done"] = True
        try:
            on_stop()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", do_stop)

    tk.Label(root, text=keys.BRAND_NAME, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 0))
    tk.Label(
        root, text=f"Developed by {keys.BRAND_COMPANY}  |  {keys.BRAND_EDITION}",
        font=("Segoe UI", 9), fg="#666666",
    ).pack(anchor="w", padx=16, pady=(0, 12))

    tk.Label(root, text="Status: Running", font=("Segoe UI", 11, "bold"), fg="#1a7f37").pack(anchor="w", padx=16)
    tk.Label(root, text=f"Local address: {base_url}", font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(2, 0))

    # Required Student Edition surface: Licensed Student / Evaluation
    # Period / Days Remaining, each on its own line (spec lists these as
    # three distinct pieces of information, not one combined string).
    student_var = tk.StringVar(value=f"Licensed Student: {status.student_tag or 'Student'}")
    period_var = tk.StringVar(value=f"Evaluation Period: {keys.LICENSE_DURATION_DAYS} days")
    days_var = tk.StringVar(value=f"Days Remaining: {_format_days_remaining(status.seconds_remaining)}")
    detail_var = tk.StringVar(value=_format_remaining(status.seconds_remaining))

    info_frame = tk.Frame(root)
    info_frame.pack(anchor="w", padx=16, pady=(10, 12))
    tk.Label(info_frame, textvariable=student_var, font=("Segoe UI", 9), fg="#444444").pack(anchor="w")
    tk.Label(info_frame, textvariable=period_var, font=("Segoe UI", 9), fg="#444444").pack(anchor="w")
    tk.Label(info_frame, textvariable=days_var, font=("Segoe UI", 9, "bold"), fg="#444444").pack(anchor="w")
    tk.Label(info_frame, textvariable=detail_var, font=("Segoe UI", 8), fg="#888888").pack(anchor="w", pady=(2, 0))

    def open_browser():
        webbrowser.open(base_url + "/docs")

    tk.Button(
        root, text="Open in Browser", font=("Segoe UI", 10, "bold"),
        command=open_browser, bg="#1a73e8", fg="white",
        activebackground="#1558b0", activeforeground="white",
        relief="flat", padx=12, pady=6, cursor="hand2",
    ).pack(anchor="w", padx=16, pady=(0, 8))

    btn_row = tk.Frame(root)
    btn_row.pack(anchor="w", padx=16)
    tk.Button(
        btn_row, text="Stop && Exit", font=("Segoe UI", 10),
        command=do_stop, relief="flat", padx=12, pady=6, cursor="hand2",
    ).pack(side="left")
    tk.Button(
        btn_row, text="About", font=("Segoe UI", 10),
        command=lambda: show_about_dialog(root), relief="flat", padx=12, pady=6, cursor="hand2",
    ).pack(side="left", padx=(8, 0))

    tk.Label(
        root, text="Closing this window stops the application and the local database.",
        font=("Segoe UI", 8), fg="#888888", wraplength=440, justify="left",
    ).pack(side="bottom", padx=16, pady=10)
    tk.Label(
        root, textvariable=tk.StringVar(value=keys.BRAND_COPYRIGHT),
        font=("Segoe UI", 7), fg="#aaaaaa",
    ).pack(side="bottom", padx=16)

    def periodic_check():
        if stopped["done"]:
            return
        latest = on_check_expired()
        if latest.expired:
            days_var.set("Days Remaining: 0 days")
            detail_var.set("Evaluation Expired")
            from tkinter import messagebox
            messagebox.showerror(
                f"{keys.BRAND_NAME} - Evaluation Expired",
                f"Evaluation Expired.\nPlease contact {keys.BRAND_COMPANY}.",
            )
            do_stop()
            return
        days_var.set(f"Days Remaining: {_format_days_remaining(latest.seconds_remaining)}")
        detail_var.set(_format_remaining(latest.seconds_remaining))
        root.after(_CHECK_INTERVAL_MS, periodic_check)

    root.after(_CHECK_INTERVAL_MS, periodic_check)
    root.mainloop()
