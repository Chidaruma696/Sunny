"""User settings shared by the window and the command line: API key and model.

Stored with QSettings when Qt is available (the registry on Windows, like Cirno), so the CLI
reads what the window saved. Without Qt, only the environment is consulted.
"""

from __future__ import annotations

import os

from . import APP_NAME

ORG = "Chidaruma"


def load_settings() -> dict:
    out = {"api_key": os.environ.get("ANTHROPIC_API_KEY", ""), "model": ""}
    try:
        from PySide6.QtCore import QSettings
    except ImportError:  # pragma: no cover
        return out
    s = QSettings(ORG, APP_NAME)
    saved_key = s.value("api_key", "")
    if saved_key:
        out["api_key"] = str(saved_key)
    out["model"] = str(s.value("model", "") or "")
    return out


def save_settings(api_key: str, model: str) -> None:
    from PySide6.QtCore import QSettings

    s = QSettings(ORG, APP_NAME)
    s.setValue("api_key", api_key)
    s.setValue("model", model)
