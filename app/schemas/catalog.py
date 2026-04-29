from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CatalogImport(BaseModel):
    name: str
    vendor: str | None = None
    version: str | None = None
    fields_json: str | None = None


class CatalogRead(BaseModel):
    id: int
    source: str
    request_id: int | None
    name: str
    vendor: str | None
    version: str | None
    status: str
    effective_from: datetime | None
    last_recertified_at: datetime | None
    fields_json: str | None

    model_config = {"from_attributes": True}
