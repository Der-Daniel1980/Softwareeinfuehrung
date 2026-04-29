from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str  # Not EmailStr - demo uses .local domains
    name: str
    password: str
    role_codes: list[str] = []


class UserRead(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    created_at: datetime
    roles: list[str] = []

    model_config = {"from_attributes": True}
