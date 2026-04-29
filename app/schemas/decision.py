from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DecisionSet(BaseModel):
    field_key: str
    role_id: int
    status: str  # IN_PROGRESS | IN_REVIEW | APPROVED | REJECTED | ACKNOWLEDGED
    comment: str | None = None


class DecisionRead(BaseModel):
    id: int
    request_id: int
    field_key: str
    role_id: int
    status: str
    decided_by: int | None
    decided_at: datetime | None
    comment: str | None

    model_config = {"from_attributes": True}
