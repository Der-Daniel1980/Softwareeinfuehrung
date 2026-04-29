from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_deps import require_admin
from app.core.csrf import verify_api_csrf
from app.core.security import hash_password
from app.database import get_db
from app.models import Role, User
from app.models.enums import AuditAction
from app.schemas.user import UserCreate, UserRead
from app.services import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> list[UserRead]:
    users = db.query(User).all()
    return [
        UserRead(
            id=u.id,
            email=u.email,
            name=u.name,
            is_active=u.is_active,
            created_at=u.created_at,
            roles=[r.code for r in u.roles],
        )
        for u in users
    ]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_api_csrf)])
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> UserRead:
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    for code in body.role_codes:
        role = db.query(Role).filter(Role.code == code).first()
        if role:
            user.roles.append(role)
    db.add(user)
    audit.log(db, admin, AuditAction.USER_CREATED.value, "User", body.email)
    db.commit()
    db.refresh(user)
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        created_at=user.created_at,
        roles=[r.code for r in user.roles],
    )
