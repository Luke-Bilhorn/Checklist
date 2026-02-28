"""Simple JSON config for app settings."""

from __future__ import annotations

import json

from .paths import get_data_dir

DEFAULT_MAX_ITEM_WIDTH = 800
MIN_MAX_ITEM_WIDTH = 400
MAX_MAX_ITEM_WIDTH = 1400


def _config_path():
    return get_data_dir() / "config.json"


def load_max_item_width() -> int:
    try:
        data = json.loads(_config_path().read_text())
        w = int(data.get("max_item_width", DEFAULT_MAX_ITEM_WIDTH))
        return max(MIN_MAX_ITEM_WIDTH, min(MAX_MAX_ITEM_WIDTH, w))
    except Exception:
        return DEFAULT_MAX_ITEM_WIDTH


def save_max_item_width(value: int) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        pass
    data["max_item_width"] = value
    path.write_text(json.dumps(data, indent=2))
