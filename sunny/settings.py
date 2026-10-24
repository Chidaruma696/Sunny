"""User settings, stored with QSettings (the registry on Windows, like Cirno)."""

from __future__ import annotations

from . import APP_NAME

ORG = "Chidaruma"


def load_settings() -> dict:
    out = {"check_updates": True}
    try:
        from PySide6.QtCore import QSettings
    except ImportError:  # pragma: no cover
        return out
    s = QSettings(ORG, APP_NAME)
    out["check_updates"] = s.value("check_updates", True, type=bool)
    return out


def save_settings(check_updates: bool = True) -> None:
    from PySide6.QtCore import QSettings

    s = QSettings(ORG, APP_NAME)
    s.setValue("check_updates", check_updates)
