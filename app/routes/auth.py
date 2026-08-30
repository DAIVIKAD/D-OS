from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import (
    CSRF_COOKIE,
    create_session_cookie,
    make_csrf_token,
    optional_user,
    require_csrf,
    require_user,
)
from app.firebase.firebase import firebase_web_config, is_web_configured
from app.services.profile_service import ensure_user_profile

router = APIRouter()


def _auth_template(request: Request, template: str, page_title: str):
    csrf = make_csrf_token()
    response = templates.TemplateResponse(
        template,
        context(
            request,
            None,
            page_title=page_title,
            error=None,
            success=None,
            firebase_ready=is_web_configured(),
        ),
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        max_age=60 * 20,
    )
    return response


@router.get("/login")
def login_page(request: Request):
    if optional_user(request):
        return RedirectResponse("/", status_code=303)
    return _auth_template(request, "auth/login.html", "Login")


@router.get("/register")
def register_page(request: Request):
    if optional_user(request):
        return RedirectResponse("/", status_code=303)
    return _auth_template(request, "auth/register.html", "Register")


@router.get("/forgot-password")
def forgot_password_page(request: Request):
    return _auth_template(request, "auth/forgot_password.html", "Forgot Password")


@router.get("/auth/firebase-config")
def web_config():
    config = firebase_web_config()
    return {"configured": is_web_configured(), "config": config}


@router.post("/session-login")
async def session_login(request: Request):
    payload = await request.json()
    require_csrf(request, request.headers.get("X-CSRF-Token", ""))
    id_token = str(payload.get("idToken", ""))
    if not id_token:
        return JSONResponse({"detail": "Missing Firebase ID token"}, status_code=400)
    try:
        session_cookie, claims = create_session_cookie(id_token)
        ensure_user_profile(
            uid=str(claims["uid"]),
            email=str(claims.get("email", "")),
            username=str(claims.get("name") or claims.get("email", "D OS User")),
        )
    except Exception as exc:
        logging.error("session-login failed: %s", exc)
        return JSONResponse({"detail": "Authentication failed. Please try again."}, status_code=401)
    response = JSONResponse({"status": "success"})
    response.set_cookie(
        settings.session_cookie_name,
        session_cookie,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_days * 24 * 60 * 60,
    )
    return response


@router.post("/logout")
@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(CSRF_COOKIE)
    return response


@router.get("/profile")
def profile_redirect(user: dict = Depends(require_user)):
    return RedirectResponse("/settings#profile", status_code=303)
