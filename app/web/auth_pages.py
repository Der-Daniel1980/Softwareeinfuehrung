"""Web auth — HTML login/logout. Rate-limited; respects is_active."""
# NOTE: No `from __future__ import annotations` here — slowapi decorator
# wraps the function and inspects __annotations__.

import os
import secrets

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import settings
from app.core.csrf import CSRF_COOKIE_NAME, generate_csrf_token
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models import User
from app.web.templates import templates

_TESTING = os.environ.get("TESTING", "0") == "1"
limiter = Limiter(key_func=get_remote_address, enabled=not _TESTING)
router = APIRouter(tags=["web-auth"])


def _set_csrf_cookie(response: Response) -> None:
    """Issue a fresh CSRF token cookie on every login-page render and login."""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=generate_csrf_token(),
        httponly=False,  # JS reads this and copies into X-CSRF-Token header
        samesite="lax",
        secure=bool(settings.SECURE_COOKIES),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    response = templates.TemplateResponse("login.html", {"request": request})
    _set_csrf_cookie(response)
    return response


@router.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> Response:
    user = db.query(User).filter(User.email == email).first()
    # Constant-time-ish: verify_password runs even on missing user to avoid
    # leaking which emails exist via response timing
    valid_pw = verify_password(password, user.password_hash) if user else False
    if not user or not valid_pw:
        resp = templates.TemplateResponse(
            "login.html", {"request": request, "error": "Ungültige Anmeldedaten"}
        )
        _set_csrf_cookie(resp)
        return resp
    if not user.is_active:
        resp = templates.TemplateResponse(
            "login.html", {"request": request, "error": "Konto ist deaktiviert"}
        )
        _set_csrf_cookie(resp)
        return resp

    token = create_access_token({"sub": str(user.id)})
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=bool(settings.SECURE_COOKIES),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    # Issue a fresh CSRF token tied to the new session
    resp.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(32),
        httponly=False,
        samesite="lax",
        secure=bool(settings.SECURE_COOKIES),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return resp


@router.post("/logout")
async def logout_web() -> RedirectResponse:
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token")
    resp.delete_cookie(CSRF_COOKIE_NAME)
    return resp
