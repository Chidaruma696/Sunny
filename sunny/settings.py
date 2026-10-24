"""User settings shared by the window and the command line: API key and model.

Stored with QSettings when Qt is available (the registry on Windows, like Cirno), so the CLI
reads what the window saved. Without Qt, only the environment is consulted.
"""

from __future__ import annotations

import os

from . import APP_NAME

ORG = "Chidaruma"


def load_settings() -> dict:
    """use_model is off by default: Sunny understands Spanish on its own, Claude is an opt-in extra."""
    out = {"api_key": os.environ.get("ANTHROPIC_API_KEY", ""), "model": "", "use_model": False}
    try:
        from PySide6.QtCore import QSettings
    except ImportError:  # pragma: no cover
        return out
    s = QSettings(ORG, APP_NAME)
    saved_key = s.value("api_key", "")
    if saved_key:
        out["api_key"] = str(saved_key)
    out["model"] = str(s.value("model", "") or "")
    out["use_model"] = s.value("use_model", False, type=bool)
    return out


def save_settings(api_key: str, model: str, use_model: bool = False) -> None:
    from PySide6.QtCore import QSettings

    s = QSettings(ORG, APP_NAME)
    s.setValue("api_key", api_key)
    s.setValue("model", model)
    s.setValue("use_model", use_model)
