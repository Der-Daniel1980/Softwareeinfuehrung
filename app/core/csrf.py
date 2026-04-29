from __future__ import annotations

import secrets

from fastapi import Cookie, HTTPException, Request, status

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(
    request: Request,
    csrf_token: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
) -> None:
    """Verify CSRF token for state-changing requests on web routes."""
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_token or not header_token or not secrets.compare_digest(csrf_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch"
        )


def verify_api_csrf(request: Request) -> None:
    """For API routes: presence of custom header X-CSRF-Token is sufficient
    (browsers cannot set custom headers on cross-origin requests without CORS
    preflight, which we restrict via CORSMiddleware). Combined with
    SameSite=Lax cookies this gives reasonable CSRF defense for the demo.
    """
    csrf_header = request.headers.get(CSRF_HEADER_NAME.lower()) or request.headers.get(
        CSRF_HEADER_NAME
    )
    htmx_header = request.headers.get("hx-request")
    if csrf_header or htmx_header:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed"
    )
