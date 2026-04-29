"""Shared Jinja2Templates instance with custom filters and globals."""
from __future__ import annotations

import json
from datetime import datetime

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

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
