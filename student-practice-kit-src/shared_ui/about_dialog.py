"""
launcher/about_dialog.py - the "About" and "Version" surfaces required by
the branding spec. Kept as two distinct dialogs (About is the marketing-
style summary; Version is the compact build/edition readout) even though
they share most of their content, since the brief calls them out as two
separate named screens.

The text-building functions (`about_text()`, `version_text()`) are plain
functions with no Tkinter dependency, specifically so they can be unit
tested (see tests/test_branding_text.py) without needing a display - CI/
build machines running `pytest` as build.bat's gate do not necessarily
have one.
"""

import tkinter as tk
from tkinter import messagebox

from licensing import keys


def about_text() -> str:
    """Matches the spec's required About Screen content exactly:
    product name, version, developer line, and copyright."""
    return (
        f"{keys.BRAND_NAME}\n"
        f"Version {keys.BRAND_VERSION}\n"
        f"Developed by {keys.BRAND_COMPANY}\n\n"
        f"{keys.BRAND_COPYRIGHT}"
    )


def version_text() -> str:
    """Compact build/edition readout - product, version, edition, and the
    license payload format version (useful for support requests: a student
    or instructor reporting an issue can quote this exactly)."""
    from licensing.keys import LICENSE_FORMAT_VERSION
    return (
        f"{keys.BRAND_NAME}\n"
        f"Version: {keys.BRAND_VERSION}\n"
        f"Edition: {keys.BRAND_EDITION}\n"
        f"License format: v{LICENSE_FORMAT_VERSION}"
    )


def show_about_dialog(parent=None):
    messagebox.showinfo(f"{keys.BRAND_NAME} - About", about_text(), parent=parent)


def show_version_dialog(parent=None):
    messagebox.showinfo(f"{keys.BRAND_NAME} - Version", version_text(), parent=parent)
