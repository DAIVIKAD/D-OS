from __future__ import annotations

import secrets
import time
from datetime import timedelta
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth

from app.core.config import settings
from app.firebase.firebase import get_firebase_app
from app.services.profile_service import get_user_profile

CSRF_COOKIE = "dos_csrf"


def make_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def create_session_cookie(id_token: str, remember_me: bool = True) -> tuple[str, dict[str, Any]]:
    app = get_firebase_app()
    decoded = auth.verify_id_token(id_token, app=app)
    if time.time() - int(decoded.get("auth_time", 0)) > 5 * 60:
        raise ValueError("Recent sign-in required")
    expires_in = timedelta(days=settings.session_days) if remember_me else timedelta(days=1)
    session_cookie = auth.create_session_cookie(
        id_token,
        expires_in=expires_in,
        app=app,
    )
    return session_cookie, decoded


def verify_session_cookie(session_cookie: str) -> dict[str, Any]:
    return auth.verify_session_cookie(
        session_cookie,
        check_revoked=False,
        app=get_firebase_app(),
    )


def optional_user(request: Request) -> dict[str, Any] | None:
    session_cookie = request.cookies.get(settings.session_cookie_name)
    if not session_cookie:
        return None
    try:
        claims = verify_session_cookie(session_cookie)
    except Exception:
        return None
    uid = str(claims["uid"])
    return get_user_profile(
        uid=uid,
        email=str(claims.get("email", "")),
        username=str(claims.get("name") or claims.get("email", "D OS User")),
    )


def require_user(request: Request) -> dict[str, Any]:
    user = optional_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
            detail="Login required",
        )
    return user


def require_csrf(request: Request, csrf_token: str) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if not csrf_token or csrf_token != cookie_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
