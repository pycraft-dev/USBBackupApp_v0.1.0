"""Application path/version helpers shared by startup and UI layers."""

from pathlib import Path
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION_PATH = PROJECT_ROOT / "VERSION"


def resolve_app_state_path() -> Path:
    """Resolve persistent app-state path for dev and frozen builds."""
    if getattr(sys, "frozen", False):
        appdata = os.getenv("APPDATA", "").strip()
        if appdata:
            return Path(appdata) / "USBBackupApp" / "app_state.json"
        return Path.home() / ".usb-backup-app" / "app_state.json"
    return PROJECT_ROOT / "config" / "app_state.json"


def resource_path(relative_path: str) -> Path:
    """Return resource path both in source mode and PyInstaller bundle."""
    base = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    return base / relative_path


def read_version() -> str:
    """Read app version from VERSION file with bundled fallback."""
    for p in (VERSION_PATH, resource_path("VERSION")):
        try:
            v = p.read_text(encoding="utf-8").strip()
            if v:
                return v
        except OSError:
            continue
    return "0.0.0"
