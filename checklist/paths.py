"""Resolve data and resource paths for both development and bundled (PyInstaller) modes."""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

APP_NAME = "Checklist"

_DEFAULT_CONFIG = "config.json"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _defaults_dir() -> Path:
    """Read-only defaults shipped with the app (committed to the repo)."""
    if is_frozen():
        return Path(sys._MEIPASS) / "defaults"
    return Path(__file__).resolve().parent.parent / "defaults"


def get_data_dir() -> Path:
    """Writable per-user directory for checklists and config.

    - Frozen app  -> platform-appropriate Application Support / AppData dir
    - Development -> the project-local ``data/`` folder (existing behaviour)
    """
    if not is_frozen():
        return Path(__file__).resolve().parent.parent / "data"

    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        import os
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        import os
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / APP_NAME


def seed_user_data() -> None:
    """On first launch, copy bundled defaults into the user data dir."""
    data_dir = get_data_dir()
    if data_dir.exists():
        return

    data_dir.mkdir(parents=True, exist_ok=True)
    defaults = _defaults_dir()

    cfg_src = defaults / _DEFAULT_CONFIG
    if cfg_src.exists():
        shutil.copy2(cfg_src, data_dir / _DEFAULT_CONFIG)

    for xml in defaults.glob("*.xml"):
        dest = data_dir / xml.name
        if not dest.exists():
            shutil.copy2(xml, dest)
