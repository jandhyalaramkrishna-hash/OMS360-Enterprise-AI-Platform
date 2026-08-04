"""
launcher/splash.py - the branded splash window shown immediately when a
student double-clicks OMS360 Enterprise AI Platform.exe, and again while
the embedded database/app are being prepared.

Design note on responsiveness (read this before "fixing" it): this splash
does NOT run on a background thread. `Splash.set_status()` repaints the
window (`update_idletasks()` + `update()`) each time the caller reports a
new step, but between two calls - e.g. while `mysqld --initialize-insecure`
is actually running - the window will not repaint and Windows may
label it "Not Responding" for a few seconds. That is a deliberate
simplicity/robustness trade-off: db_provisioner.py's subprocess calls are
Windows-specific and were never run against a real Windows machine from
the Linux sandbox this kit was authored in, so this file avoids adding
threading (locks, cross-thread Tkinter calls, exception propagation from a
worker thread back to the UI) on top of code that already couldn't be
exercised end-to-end here. A short "Not Responding" flash during a one-time,
few-second provisioning step is a fair trade against a background-threading
bug that could not have been tested before shipping. If this is ever felt
in practice, moving `db_provisioner.provision()`/`start_mysqld()` onto a
worker thread and marshalling status updates back via `root.after()` is the
follow-up - see build/README.md's verification checklist item 3.
"""

import tkinter as tk

from licensing import keys


class Splash:
    """A small always-on-top branded window with one status line. Call
    set_status(...) at each meaningful step; call close() when done."""

    def __init__(self, initial_status: str = "Starting..."):
        self.root = tk.Tk()
        self.root.title(keys.BRAND_NAME)
        self.root.overrideredirect(True)  # no title bar/border - a real splash
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        width, height = 460, 220
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        frame = tk.Frame(self.root, bg="#0b1f3a", padx=24, pady=24)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame, text=keys.BRAND_NAME, font=("Segoe UI", 16, "bold"),
            bg="#0b1f3a", fg="white",
        ).pack(anchor="w")
        tk.Label(
            frame, text=f"Developed by {keys.BRAND_COMPANY}",
            font=("Segoe UI", 9), bg="#0b1f3a", fg="#b7c4d9",
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            frame, text=keys.BRAND_EDITION,
            font=("Segoe UI", 9, "italic"), bg="#0b1f3a", fg="#b7c4d9",
        ).pack(anchor="w", pady=(0, 20))

        self._status_var = tk.StringVar(value=initial_status)
        tk.Label(
            frame, textvariable=self._status_var, font=("Segoe UI", 10),
            bg="#0b1f3a", fg="#e8edf5", wraplength=412, justify="left",
        ).pack(anchor="w", side="bottom")

        tk.Label(
            frame, text=f"Version {keys.BRAND_VERSION}", font=("Segoe UI", 8),
            bg="#0b1f3a", fg="#7d8ba3",
        ).pack(anchor="e", side="bottom", pady=(0, 8))

        self._pump()

    def set_status(self, text: str):
        self._status_var.set(text)
        self._pump()

    def _pump(self):
        """Force an immediate repaint. Safe to call often - the underlying
        Tk calls are cheap no-ops when there is nothing new to draw."""
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            pass  # window already closed

    def close(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def show_splash(initial_status: str = "Starting...") -> Splash:
    return Splash(initial_status)
