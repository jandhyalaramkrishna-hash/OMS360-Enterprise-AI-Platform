"""
launcher/activation_ui.py - the first-run "enter your License Key" dialog,
and the "Evaluation Expired" message. Tkinter, matching generator/main.py's
toolkit choice (stdlib, no extra runtime dependency to bundle).
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext

from shared_ui.about_dialog import show_about_dialog
from shared_ui.icon import PLATFORM_ICON_NAME, set_window_icon
from licensing import keys
from licensing.errors import LicenseError
from licensing.gate import LicenseGate


def prompt_for_license_key(gate: LicenseGate):
    """Blocks until the user enters a valid key or closes the dialog.
    Returns the resulting ActivationStatus on success, or None if the
    user closed the window without activating (caller should exit)."""
    result = {"status": None}

    root = tk.Tk()
    root.title(f"{keys.BRAND_NAME} - Activation")
    root.resizable(False, False)
    root.geometry("560x400")
    set_window_icon(root, PLATFORM_ICON_NAME)

    tk.Label(
        root, text=keys.BRAND_NAME, font=("Segoe UI", 14, "bold"),
    ).pack(anchor="w", padx=16, pady=(16, 0))
    tk.Label(
        root, text=f"Developed by {keys.BRAND_COMPANY}  |  {keys.BRAND_EDITION}",
        font=("Segoe UI", 9), fg="#666666",
    ).pack(anchor="w", padx=16, pady=(0, 12))

    tk.Label(
        root,
        text=f"Enter your License Key to begin your "
             f"{keys.LICENSE_DURATION_DAYS}-day evaluation.\n"
             f"Paste the full key exactly as provided by your instructor.",
        font=("Segoe UI", 10), justify="left",
    ).pack(anchor="w", padx=16)

    key_box = scrolledtext.ScrolledText(root, height=6, width=62, font=("Consolas", 10), wrap="char")
    key_box.pack(anchor="w", padx=16, pady=(8, 4))
    key_box.focus_set()

    status_var = tk.StringVar(value="")
    status_label = tk.Label(root, textvariable=status_var, font=("Segoe UI", 9), fg="#c0392b", justify="left")
    status_label.pack(anchor="w", padx=16)

    def on_activate():
        key_text = key_box.get("1.0", tk.END)
        if not key_text.strip():
            status_var.set("Enter a license key first.")
            return
        try:
            status = gate.activate_with_key(key_text)
        except LicenseError as exc:
            status_var.set(str(exc))
            return
        result["status"] = status
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(anchor="w", padx=16, pady=10)

    tk.Button(
        btn_frame, text="Activate", font=("Segoe UI", 11, "bold"),
        command=on_activate, bg="#1a73e8", fg="white",
        activebackground="#1558b0", activeforeground="white",
        relief="flat", padx=14, pady=6, cursor="hand2",
    ).pack(side="left")

    tk.Button(
        btn_frame, text="Exit", font=("Segoe UI", 11),
        command=root.destroy, relief="flat", padx=14, pady=6, cursor="hand2",
    ).pack(side="left", padx=(8, 0))

    tk.Button(
        btn_frame, text="About", font=("Segoe UI", 11),
        command=lambda: show_about_dialog(root), relief="flat", padx=14, pady=6, cursor="hand2",
    ).pack(side="left", padx=(8, 0))

    tk.Label(
        root, text="Don't have a key? Contact your instructor or ZelQA Technologies.",
        font=("Segoe UI", 8), fg="#888888",
    ).pack(side="bottom", pady=(4, 0))
    tk.Label(
        root, text=keys.BRAND_COPYRIGHT, font=("Segoe UI", 7), fg="#aaaaaa",
    ).pack(side="bottom", pady=(0, 10))

    root.mainloop()
    return result["status"]


def show_evaluation_expired():
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        f"{keys.BRAND_NAME} - Evaluation Expired",
        f"Evaluation Expired.\nPlease contact {keys.BRAND_COMPANY}.",
    )
    root.destroy()


def show_fatal_error(title: str, message: str):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(f"{keys.BRAND_NAME} - {title}", message)
    root.destroy()
