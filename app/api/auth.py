"""Auth API – login, logout, me."""
# NOTE: Do NOT use `from __future__ import annotations` in this module.
# The slowapi @limiter.limit decorator wraps the function and loses
# the module-level __annotations__ context needed for Pydantic to
# resolve forward references.  Import types explicitly instead.

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth_deps import get_current_user
from app.core.csrf import CSRF_COOKIE_NAME, generate_csrf_token
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models import User
from app.models.enums import AuditAction
from app.schemas.auth import LoginRequest, MeResponse
from app.services import audit

# Rate limiter – enabled only outside of tests
_TESTING = os.environ.get("TESTING", "0") == "1"
limiter = Limiter(key_func=get_remote_address, enabled=not _TESTING)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    token = create_access_token({"sub": str(user.id)})
    audit.log(db, user, AuditAction.LOGIN.value, "User", str(user.id))
    db.commit()

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=bool(settings.SECURE_COOKIES),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    # Issue CSRF token (readable by JS, sent back as X-CSRF-Token header)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=generate_csrf_token(),
        httponly=False,
        samesite="lax",
        secure=bool(settings.SECURE_COOKIES),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"ok": True}


@router.post("/logout")
async def logout(
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    audit.log(db, user, AuditAction.LOGOUT.value, "User", str(user.id))
    db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie(CSRF_COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=[r.code for r in user.roles],
        is_active=user.is_active,
    )
