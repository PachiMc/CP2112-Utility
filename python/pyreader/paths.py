"""Path helpers for development and PyInstaller-frozen builds."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _PACKAGE_DIR.parent


def bundle_dir() -> Path:
    """Directory where bundled resources and DLLs live at runtime."""
    if getattr(sys, 'frozen', False):
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    return _PACKAGE_DIR


def vendor_dll_dir() -> Path:
    """Directory containing Silicon Labs runtime DLLs (dev / build)."""
    return _PROJECT_DIR / 'vendor'


def resource_path(filename: str) -> Path:
    """Return the path to a file bundled with the application."""
    return bundle_dir() / filename


def user_data_dir() -> Path:
    """Writable per-user directory for logs and exports."""
    if getattr(sys, 'frozen', False):
        base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CP2112-Battery-Analyzer'
    else:
        base = _PACKAGE_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base


def dll_search_dirs() -> list[Path]:
    """Directories to search for SLABHIDtoSMBus.dll (first match wins)."""
    dirs: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            dirs.append(resolved)

    add(bundle_dir())
    add(vendor_dll_dir())
    add(_PACKAGE_DIR)
    add(_PROJECT_DIR)
    add(Path.cwd())

    if getattr(sys, 'frozen', False):
        add(Path(sys.executable).resolve().parent)

    return dirs
