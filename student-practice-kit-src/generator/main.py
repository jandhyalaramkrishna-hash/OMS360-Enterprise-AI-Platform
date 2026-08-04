"""
generator/main.py - OMS360 License Generator (internal ZelQA Technologies
tool). Entry point for OMS360 License Generator.exe.

UI, per the spec, is deliberately minimal - nothing beyond:

    Student Name
    [______________]
    [Generate License Key]

...plus a read-only output box to copy the resulting key from (unavoidable
- the operator has to get the key out of the app somehow) and a status
line. No duration control, no key-management screen, no settings - the
7-day duration is a constant imported from licensing.keys, not something
this UI can change (see that module's docstring).

The signing private key (generator/_signing_key.py) is never displayed
anywhere in this UI - only the resulting, already-signed license key text
is ever shown or copied.
"""

import csv
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, scrolledtext

from generator._signing_key import load_private_key
from shared_ui.about_dialog import show_about_dialog
from shared_ui.icon import GENERATOR_ICON_NAME, set_window_icon
from licensing import codec, keys


def _issue_log_path() -> Path:
    """Local, append-only record of every key this installation of the
    Generator has issued - student name, license id, timestamp. Purely a
    convenience for ZelQA staff (e.g. 'did I already generate one for
    this student'); it plays no role in validating keys - the app never
    reads this file, only appends to it. Kept next to the exe so it
    travels with whichever machine is running the Generator."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "license_issue_log.csv"


def _append_issue_log(student_name: str, license_id_hex: str, key: str):
    log_path = _issue_log_path()
    is_new = not log_path.exists()
    try:
        with log_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["issued_at_utc", "student_name", "license_id", "license_key"])
            writer.writerow([
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                student_name,
                license_id_hex,
                key,
            ])
    except OSError:
        # Logging is a convenience, not a requirement - a locked/read-only
        # folder should never prevent issuing a key.
        pass


class GeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{keys.BRAND_NAME} - License Generator ({keys.BRAND_COMPANY}, Internal Tool)")
        self.resizable(False, False)
        self.geometry("560x420")
        set_window_icon(self, GENERATOR_ICON_NAME)
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 16, "pady": 6}

        header = tk.Label(
            self, text="OMS360 License Generator",
            font=("Segoe UI", 14, "bold"),
        )
        header.pack(anchor="w", **pad)

        subheader = tk.Label(
            self,
            text=f"Internal tool for {keys.BRAND_COMPANY} staff only.\n"
                 f"Every key generated here is valid for exactly "
                 f"{keys.LICENSE_DURATION_DAYS} days from the student's first activation.",
            font=("Segoe UI", 9), fg="#444444", justify="left",
        )
        subheader.pack(anchor="w", **pad)

        tk.Label(self, text="Student Name", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16)
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(self, textvariable=self.name_var, font=("Segoe UI", 11), width=40)
        self.name_entry.pack(anchor="w", padx=16, pady=(2, 10))
        self.name_entry.focus_set()
        self.name_entry.bind("<Return>", lambda _e: self._on_generate())

        self.generate_btn = tk.Button(
            self, text="Generate License Key", font=("Segoe UI", 11, "bold"),
            command=self._on_generate, bg="#1a73e8", fg="white",
            activebackground="#1558b0", activeforeground="white",
            relief="flat", padx=14, pady=8, cursor="hand2",
        )
        self.generate_btn.pack(anchor="w", padx=16, pady=(0, 14))

        tk.Label(self, text="Generated License Key", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16)
        self.output_box = scrolledtext.ScrolledText(
            self, height=8, width=62, font=("Consolas", 10), wrap="char",
            state="disabled", bg="#f5f5f5",
        )
        self.output_box.pack(anchor="w", padx=16, pady=(2, 8))

        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(self, textvariable=self.status_var, font=("Segoe UI", 9), fg="#1a7f37")
        self.status_label.pack(anchor="w", padx=16)

        footer = tk.Label(
            self, text=f"{keys.BRAND_NAME}  v{keys.BRAND_VERSION}  |  Developed by {keys.BRAND_COMPANY}",
            font=("Segoe UI", 8), fg="#888888",
        )
        footer.pack(side="bottom", pady=(2, 0))
        tk.Label(
            self, text=keys.BRAND_COPYRIGHT, font=("Segoe UI", 7), fg="#aaaaaa",
        ).pack(side="bottom", pady=(0, 2))
        tk.Button(
            self, text="About", font=("Segoe UI", 8),
            command=lambda: show_about_dialog(self), relief="flat", cursor="hand2",
        ).pack(side="bottom", pady=(4, 0))

    def _on_generate(self):
        student_name = self.name_var.get().strip()
        if not student_name:
            messagebox.showwarning(
                "Student Name required",
                "Enter the student's name before generating a license key.",
            )
            self.name_entry.focus_set()
            return

        try:
            private_key = load_private_key()
            key = codec.issue_license(student_name, private_key)
        except Exception as exc:  # pragma: no cover - defensive UI guard
            messagebox.showerror("License generation failed", str(exc))
            return

        payload = codec.verify_license(key)  # sanity self-check before showing it
        _append_issue_log(student_name, payload.license_id_hex, key)

        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, key)
        self.output_box.configure(state="disabled")

        self.clipboard_clear()
        self.clipboard_append(key)

        self.status_var.set(
            f"Generated for '{student_name}' (license id {payload.license_id_hex}) "
            f"and copied to clipboard."
        )


def main():
    app = GeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
