from __future__ import annotations

from app.config import get_settings

_auto_drops_enabled = get_settings().auto_drops_enabled


def auto_drops_enabled() -> bool:
    return _auto_drops_enabled


def set_auto_drops_enabled(value: bool) -> None:
    global _auto_drops_enabled
    _auto_drops_enabled = value
