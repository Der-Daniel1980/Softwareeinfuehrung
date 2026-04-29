from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CommentCreate(BaseModel):
    body: str
    field_key: str | None = None
    role_id: int | None = None
    parent_id: int | None = None


class CommentRead(BaseModel):
    id: int
    request_id: int
    field_key: str | None
    role_id: int | None
    parent_id: int | None
    author_id: int
    body: str
    created_at: datetime
    edited_at: datetime | None

    model_config = {"from_attributes": True}
