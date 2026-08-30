from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.budget import router as budget_router
from app.routes.dashboard import router as dashboard_router
from app.routes.goals import router as goals_router
from app.routes.investments import router as investments_router
from app.routes.lend_borrow import router as lend_borrow_router
from app.routes.reports import router as reports_router
from app.routes.search import router as search_router
from app.routes.settings import router as settings_router
from app.routes.transactions import router as transactions_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="D-OS",
    description="D-OS MONEY OPERATING SYSTEM",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(transactions_router)
app.include_router(goals_router)
app.include_router(investments_router)
app.include_router(budget_router)
app.include_router(lend_borrow_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(search_router)


@app.middleware("http")
async def security_and_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")

    if path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=86400")
    else:
        response.headers["Cache-Control"] = "no-store, max-age=0, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Vary"] = "Cookie"
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    return RedirectResponse("/login", status_code=303)


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=not settings.is_production)
