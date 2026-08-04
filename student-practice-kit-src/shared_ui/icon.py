"""
shared_ui/icon.py - resolves the bundled .ico files and applies them to
Tkinter windows, so the title bar / taskbar / Alt+Tab icon matches the
.exe's own file icon (PyInstaller's EXE(icon=...) only sets the file icon
shown in File Explorer - Tkinter windows show a generic icon unless told
otherwise at runtime, which is what this module does).

Kept in shared_ui/ (not launcher/) for the same reason as about_dialog.py:
generator/main.py needs its own icon too, without pulling in launcher's
heavier imports.
"""

import sys
from pathlib import Path

PLATFORM_ICON_NAME = "oms360_platform.ico"
GENERATOR_ICON_NAME = "oms360_generator.ico"


def _icons_dir() -> Path:
    """Mirrors launcher/db_provisioner.py::_bundle_resource_dir()'s
    frozen-vs-source-tree resolution, kept independent here since
    shared_ui/ must not import from launcher/ (see shared_ui/__init__.py)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "resources" / "icons"
    return Path(__file__).resolve().parent.parent / "build" / "resources" / "icons"


def set_window_icon(root, icon_name: str) -> None:
    """Best-effort: sets root's title bar/taskbar icon to the bundled .ico
    matching icon_name. Silently does nothing if the icon can't be applied
    - this is cosmetic polish, never something that should be able to
    crash startup (e.g. running unfrozen on Linux/macOS during
    development, where .ico + iconbitmap isn't supported at all)."""
    icon_path = _icons_dir() / icon_name
    if not icon_path.exists():
        return
    try:
        root.iconbitmap(default=str(icon_path))
    except Exception:
        pass
