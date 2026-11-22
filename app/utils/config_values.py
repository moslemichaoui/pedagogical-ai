"""Read configuration from the active Flask app when available."""
from __future__ import annotations

from typing import Any, Optional

from flask import current_app, has_app_context

from config import Config


def config_value(name: str, default: Optional[Any] = None) -> Any:
    """Return a live config value, falling back to import-time ``Config``.

    Services are sometimes constructed outside a request (CLI scripts, tests),
    so they still need a safe import-time fallback. Inside Flask, however, the
    active app config must win: the settings page and readiness probe should
    describe the running application, not module import state.
    """
    if has_app_context():
        value = current_app.config.get(name, default)
    else:
        value = getattr(Config, name, default)
    return default if value is None else value
