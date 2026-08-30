from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.templates import templates
from app.core.view import context, is_htmx
from app.firebase.auth import require_user
from app.services.finance import search_everything

router = APIRouter()


@router.get("/search")
def search_page(request: Request, q: str = "", user: dict = Depends(require_user)):
    results = search_everything(user, q)
    template = "partials/search_results.html" if is_htmx(request) else "pages/search.html"
    return templates.TemplateResponse(
        template,
        context(request, user, page_title="Search", query=q, results=results),
    )


@router.get("/api/search")
def search_api(q: str = "", user: dict = Depends(require_user)):
    return search_everything(user, q)

