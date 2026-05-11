"""Shared Jinja2Templates instance with custom filters and globals."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def _static_version() -> str:
    """Cache-Bust-Token für /static/app.js und /static/app.css.

    Nginx cacht statische Dateien mit max-age=86400; ohne expliziten Bust
    sehen Nutzer nach einem Code-Update bis zu 24h alte JS-/CSS-Dateien.
    Wir verwenden die jüngste mtime der beiden Files (oder Server-Startzeit)
    als Version-String und hängen sie in `base.html` als ?v=… an.
    """
    candidates = [
        Path("app/static/app.js"),
        Path("app/static/app.css"),
    ]
    mtimes = [p.stat().st_mtime for p in candidates if p.exists()]
    if mtimes:
        return str(int(max(mtimes)))
    return str(int(datetime.utcnow().timestamp()))


_STATIC_VERSION = _static_version()

# ── Custom filters ─────────────────────────────────────────────────────────

def _from_json(value: str | None) -> list | dict:
    """Parse a JSON string into a Python object."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []


def _selectattr_in(iterable, attr, values):
    """Select items where item[attr] is in values list."""
    return [item for item in iterable if getattr(item, attr, None) in values]


templates.env.filters["from_json"] = _from_json

# ── Custom globals ──────────────────────────────────────────────────────────

templates.env.globals["now"] = datetime.utcnow
templates.env.globals["static_version"] = _STATIC_VERSION
