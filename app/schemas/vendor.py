from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VendorBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=255)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class VendorRead(VendorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime
