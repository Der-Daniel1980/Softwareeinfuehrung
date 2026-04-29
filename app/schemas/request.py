from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RequestCreate(BaseModel):
    title: str


class RequestPatch(BaseModel):
    title: str | None = None
    system_category: str | None = None
    application_owner_id: int | None = None
    it_application_owner_id: int | None = None
    short_description: str | None = None
    installation_location: str | None = None
    post_approval_due_date: datetime | None = None


class FieldValuePatch(BaseModel):
    value: str | None = None


class SubmitRequest(BaseModel):
    category_d_confirmed_by: list[int] = []


class ResubmitRequest(BaseModel):
    pass


class FieldValueRead(BaseModel):
    field_key: str
    value_text: str | None

    model_config = {"from_attributes": True}


class AttachmentRead(BaseModel):
    id: int
    filename: str
    mime_type: str
    size_bytes: int
    purpose: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class RequestRead(BaseModel):
    id: int
    title: str
    requester_id: int
    status: str
    system_category: str | None
    application_owner_id: int | None
    it_application_owner_id: int | None
    short_description: str | None
    installation_location: str | None
    post_approval_due_date: datetime | None
    created_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None
    field_values: list[FieldValueRead] = []
    attachments: list[AttachmentRead] = []

    model_config = {"from_attributes": True}
