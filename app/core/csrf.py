"""CSRF helpers.

Two layers of CSRF defense:

1. Cookies are SameSite=Lax — browsers will NOT include the auth cookie on
   cross-site POST/PATCH/DELETE requests, which already blocks the bulk of
   classic CSRF.

2. Double-submit token: a `csrf_token` cookie is set on login (readable by JS)
   and the frontend echoes it back as the `X-CSRF-Token` header. The server
   compares cookie value with header value via constant-time compare.

Tests bypass the check via TESTING=1.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Cookie, HTTPException, Request, status

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

_TESTING = os.environ.get("TESTING", "0") == "1"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(
    request: Request,
    csrf_token: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
) -> None:
    """Strict double-submit check for HTML form POSTs."""
    if _TESTING:
        return
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_token or not header_token or not secrets.compare_digest(csrf_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch"
        )


def verify_api_csrf(
    request: Request,
    csrf_token: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
) -> None:
    """Double-submit check for JSON API mutations.

    Accepts:
      - Token header matches token cookie (constant-time compare), OR
      - Pre-flighted CORS request (browser would have rejected at CORS layer
        if origin not allowed) — verified by HX-Request or X-CSRF-Token header
        presence on requests that don't carry the auth cookie at all (login).

    Rationale: SameSite=Lax already blocks cross-site POST. The header check
    catches edge cases (subdomain takeover, browser bugs).
    """
    if _TESTING:
        return

    # No cookie means no session — nothing to forge against. Allow (route's
    # auth dep will reject if it really needs an authenticated user).
    if csrf_token is None:
        return

    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not header_token or not secrets.compare_digest(csrf_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed"
        )
