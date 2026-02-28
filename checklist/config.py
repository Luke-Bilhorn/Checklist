"""Simple JSON config for app settings."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "config.json"

DEFAULT_MAX_ITEM_WIDTH = 800
MIN_MAX_ITEM_WIDTH = 400
MAX_MAX_ITEM_WIDTH = 1400


def load_max_item_width() -> int:
    try:
        data = json.loads(CONFIG_PATH.read_text())
        w = int(data.get("max_item_width", DEFAULT_MAX_ITEM_WIDTH))
        return max(MIN_MAX_ITEM_WIDTH, min(MAX_MAX_ITEM_WIDTH, w))
    except Exception:
        return DEFAULT_MAX_ITEM_WIDTH


def save_max_item_width(value: int) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except Exception:
        pass
    data["max_item_width"] = value
    CONFIG_PATH.write_text(json.dumps(data, indent=2))
