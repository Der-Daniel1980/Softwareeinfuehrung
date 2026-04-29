from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str  # Not EmailStr - demo uses .local domains that fail strict validation
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: str
    name: str
    roles: list[str]
    is_active: bool

    model_config = {"from_attributes": True}
