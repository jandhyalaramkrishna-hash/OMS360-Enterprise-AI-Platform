"""
tests/test_branding_text.py - covers the text-building logic behind the
About/Version dialogs (shared_ui/about_dialog.py) and the status window's
"Days Remaining" formatting (launcher/status_window.py). These are plain
functions with no Tkinter dependency, kept importable and testable without
a display - see shared_ui/about_dialog.py's module docstring for why.
"""

from launcher.status_window import _format_days_remaining, _format_remaining
from licensing import keys
from shared_ui.about_dialog import about_text, version_text


def test_about_text_contains_required_spec_lines():
    text = about_text()
    assert "OMS360 Enterprise AI Platform" in text
    assert "Version 1.0.0" in text
    assert "Developed by ZelQA Technologies" in text
    assert "© ZelQA Technologies" in text
    assert "All Rights Reserved" in text


def test_version_text_contains_edition_and_version():
    text = version_text()
    assert keys.BRAND_NAME in text
    assert keys.BRAND_VERSION in text
    assert "Student Practice Edition" in text
    assert "License format" in text


def test_format_days_remaining_under_one_day():
    assert _format_days_remaining(60) == "Less than 1 day"
    assert _format_days_remaining(3600 * 23) == "Less than 1 day"


def test_format_days_remaining_zero():
    assert _format_days_remaining(0) == "0 days"


def test_format_days_remaining_exact_days():
    assert _format_days_remaining(86400) == "1 day"
    assert _format_days_remaining(86400 * 7) == "7 days"


def test_format_days_remaining_rounds_up_partial_day():
    # 1 day + 1 second should read as 2 days (ceiling), not silently as 1.
    assert _format_days_remaining(86400 + 1) == "2 days"


def test_format_days_remaining_none_is_unknown():
    assert _format_days_remaining(None) == "unknown"


def test_format_remaining_unchanged_for_detail_line():
    # Pin down the existing detailed d/h/m formatter still works as before
    # - status_window.py's edits should not have touched its behavior.
    assert _format_remaining(None) == "unknown"
    assert _format_remaining(0) == "0m remaining"
    assert _format_remaining(90) == "1m remaining"
    assert _format_remaining(3661) == "1h 1m remaining"
    assert _format_remaining(86400 + 3600) == "1d 1h remaining"
