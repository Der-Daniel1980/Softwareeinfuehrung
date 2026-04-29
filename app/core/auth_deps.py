from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models import User


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    payload = decode_token(access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )
    return user


def require_role(*codes: str):  # type: ignore[no-untyped-def]
    """Dependency factory – raises 403 if user doesn't have one of the given roles."""

    def _check(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_role(c) for c in codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {list(codes)}",
            )
        return user

    return _check


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.has_role("ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def require_admin_or_auditor(user: User = Depends(get_current_user)) -> User:
    if not (user.has_role("ADMIN") or user.has_role("AUDITOR")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Auditor only"
        )
    return user
