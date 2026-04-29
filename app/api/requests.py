from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth_deps import get_current_user
from app.core.csrf import verify_api_csrf
from app.database import get_db
from app.models import ApplicationRequest, Attachment, FieldValue, User
from app.models.enums import AuditAction
from app.schemas.request import (
    FieldValuePatch,
    RequestCreate,
    RequestPatch,
    RequestRead,
    ResubmitRequest,
    SubmitRequest,
)
from app.services import audit, revisions, workflow

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=list[RequestRead])
def list_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RequestRead]:
    all_reqs = db.query(ApplicationRequest).all()
    return [
        _to_read(r)
        for r in all_reqs
        if workflow.can_view(r, user)
    ]


@router.post("", response_model=RequestRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_api_csrf)])
def create_request(
    body: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestRead:
    req = ApplicationRequest(
        title=body.title,
        requester_id=user.id,
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.flush()
    db.commit()
    db.refresh(req)
    return _to_read(req)


@router.get("/{req_id}", response_model=RequestRead)
def get_request(
    req_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestRead:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _to_read(req)


@router.patch("/{req_id}", response_model=RequestRead,
              dependencies=[Depends(verify_api_csrf)])
def patch_request(
    req_id: int,
    body: RequestPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestRead:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_edit(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(req, field, val)

    db.commit()
    db.refresh(req)
    return _to_read(req)


@router.patch("/{req_id}/fields/{key}", response_model=RequestRead,
              dependencies=[Depends(verify_api_csrf)])
def patch_field(
    req_id: int,
    key: str,
    body: FieldValuePatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestRead:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_edit(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit")

    fv = (
        db.query(FieldValue)
        .filter(FieldValue.request_id == req_id, FieldValue.field_key == key)
        .first()
    )
    old_val = fv.value_text if fv else None

    if fv:
        fv.value_text = body.value
        fv.updated_by = user.id
        fv.updated_at = datetime.utcnow()
    else:
        fv = FieldValue(
            request_id=req_id,
            field_key=key,
            value_text=body.value,
            updated_by=user.id,
            updated_at=datetime.utcnow(),
        )
        db.add(fv)

    db.flush()
    revisions.record_field_change(
        db, req, key, old_val, body.value, user,
        f"Feld '{key}' geändert"
    )
    audit.log(db, user, AuditAction.FIELD_UPDATED.value, "FieldValue", f"{req_id}/{key}",
              {"old": old_val, "new": body.value})
    db.commit()
    db.refresh(req)
    return _to_read(req)


@router.post("/{req_id}/submit", response_model=RequestRead,
             dependencies=[Depends(verify_api_csrf)])
def submit_request(
    req_id: int,
    body: SubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestRead:
    req = _get_req_or_404(db, req_id)
    if req.requester_id != user.id and not user.has_role("ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")

    workflow.submit(db, req, user, category_d_confirmed_by=body.category_d_confirmed_by)
    db.commit()
    db.refresh(req)
    return _to_read(req)


@router.post("/{req_id}/resubmit", response_model=RequestRead,
             dependencies=[Depends(verify_api_csrf)])
def resubmit_request(
    req_id: int,
    body: ResubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestRead:
    req = _get_req_or_404(db, req_id)
    if req.requester_id != user.id and not user.has_role("ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")

    workflow.resubmit(db, req, user)
    db.commit()
    db.refresh(req)
    return _to_read(req)


_MAX_ATTACHMENTS_PER_REQUEST = 20
_STREAM_CHUNK_SIZE = 1024 * 1024  # 1 MB
_SAFE_FILENAME_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.() äöüÄÖÜß"
)


def _sanitize_filename(name: str | None) -> str:
    if not name:
        return "datei"
    # Strip path components
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    # Remove leading dots (no hidden files), drop disallowed chars
    cleaned = "".join(c for c in name if c in _SAFE_FILENAME_CHARS).lstrip(".") or "datei"
    return cleaned[:200]


@router.post("/{req_id}/attachments", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_api_csrf)])
async def upload_attachment(
    req_id: int,
    purpose: str = "GENERIC",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_edit(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit")

    # Per-request attachment count limit (DoS protection)
    existing_count = db.query(Attachment).filter(Attachment.request_id == req_id).count()
    if existing_count >= _MAX_ATTACHMENTS_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {_MAX_ATTACHMENTS_PER_REQUEST} attachments per request reached",
        )

    # Validate client-declared MIME type against allowlist (first line of defence)
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type not allowed: {file.content_type}",
        )

    # Stream-read with running size check; abort early if quota exceeded
    storage_name = uuid.uuid4().hex  # No extension in storage path — defeats path-based execution
    upload_dir = Path(settings.UPLOAD_DIR) / str(req_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_path = upload_dir / storage_name

    bytes_written = 0
    try:
        with storage_path.open("wb") as fh:
            while True:
                chunk = await file.read(_STREAM_CHUNK_SIZE)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > settings.MAX_UPLOAD_BYTES:
                    fh.close()
                    storage_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File too large (max 25 MB)",
                    )
                fh.write(chunk)
    except HTTPException:
        raise
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise

    safe_name = _sanitize_filename(file.filename)
    attachment = Attachment(
        request_id=req_id,
        filename=safe_name,
        mime_type=file.content_type,
        storage_path=str(storage_path),
        size_bytes=bytes_written,
        purpose=purpose,
        uploaded_by=user.id,
        uploaded_at=datetime.utcnow(),
    )
    db.add(attachment)
    audit.log(db, user, AuditAction.ATTACHMENT_UPLOADED.value, "Attachment",
              str(req_id), {"filename": safe_name, "purpose": purpose, "size": bytes_written})
    db.commit()
    db.refresh(attachment)
    return {"id": attachment.id, "filename": attachment.filename}


@router.get("/{req_id}/attachments/{aid}")
def download_attachment(
    req_id: int,
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    att = db.get(Attachment, aid)
    if not att or att.request_id != req_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not os.path.exists(att.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    # Always force download (Content-Disposition: attachment) and disable MIME sniffing
    # so a malicious .html or .svg can't be rendered inline by the browser.
    return FileResponse(
        att.storage_path,
        filename=_sanitize_filename(att.filename),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{_sanitize_filename(att.filename)}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


def _get_req_or_404(db: Session, req_id: int) -> ApplicationRequest:
    req = db.get(ApplicationRequest, req_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return req


def _to_read(req: ApplicationRequest) -> RequestRead:
    from app.schemas.request import AttachmentRead, FieldValueRead

    return RequestRead(
        id=req.id,
        title=req.title,
        requester_id=req.requester_id,
        status=req.status,
        system_category=req.system_category,
        application_owner_id=req.application_owner_id,
        it_application_owner_id=req.it_application_owner_id,
        short_description=req.short_description,
        installation_location=req.installation_location,
        post_approval_due_date=req.post_approval_due_date,
        created_at=req.created_at,
        submitted_at=req.submitted_at,
        completed_at=req.completed_at,
        field_values=[
            FieldValueRead(field_key=fv.field_key, value_text=fv.value_text)
            for fv in req.field_values
        ],
        attachments=[
            AttachmentRead(
                id=a.id,
                filename=a.filename,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
                purpose=a.purpose,
                uploaded_at=a.uploaded_at,
            )
            for a in req.attachments
        ],
    )
