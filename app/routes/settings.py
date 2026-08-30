from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from firebase_admin import auth as firebase_auth

from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import require_user
from app.firebase.firebase import get_firebase_app
from app.firebase.schema import RECURRING, WISHLIST
from app.services import firestore_service as store
from app.services.profile_service import (
    add_category,
    get_categories,
    update_category,
    update_profile,
)
from app.services.finance import to_decimal
from app.utils.formatting import optional_date

router = APIRouter()


@router.get("/more")
def more_page(request: Request, user: dict = Depends(require_user)):
    return templates.TemplateResponse(
        "pages/more.html",
        context(request, user, page_title="More"),
    )


@router.get("/help")
def help_page(request: Request, user: dict = Depends(require_user)):
    return templates.TemplateResponse(
        "pages/help.html",
        context(request, user, page_title="Help Center"),
    )


@router.get("/about")
def about_page(request: Request, user: dict = Depends(require_user)):
    return templates.TemplateResponse(
        "pages/about.html",
        context(request, user, page_title="About D-OS"),
    )


@router.post("/api/onboarding-complete")
def complete_onboarding(user: dict = Depends(require_user)):
    from app.services.profile_service import profile_ref, now_iso
    profile_ref(str(user["uid"])).set(
        {"has_seen_onboarding": True, "updatedAt": now_iso()},
        merge=True,
    )
    return {"ok": True}


@router.get("/recurring")
def recurring_page(request: Request, user: dict = Depends(require_user)):
    categories = get_categories(user)
    recurring = store.list_recurring(str(user["uid"]))
    return templates.TemplateResponse(
        "pages/recurring.html",
        context(
            request,
            user,
            page_title="Recurring Payments",
            categories=categories,
            expense_categories=[category for category in categories if category.get("kind") == "expense"],
            recurring=recurring,
        ),
    )


@router.get("/settings")
def settings_page(request: Request, user: dict = Depends(require_user)):
    categories = get_categories(user)
    return templates.TemplateResponse(
        "pages/settings.html",
        context(
            request,
            user,
            page_title="Settings",
            categories=categories,
            expense_categories=[category for category in categories if category.get("kind") == "expense"],
            message=None,
        ),
    )


@router.post("/settings/profile")
def update_profile_route(
    username: str = Form(...),
    currency: str = Form("₹"),
    user: dict = Depends(require_user),
):
    update_profile(str(user["uid"]), username, currency)
    return RedirectResponse("/settings#profile", status_code=303)


@router.post("/settings/password")
def update_password(
    new_password: str = Form(...),
    user: dict = Depends(require_user),
):
    if len(new_password) >= 8:
        firebase_auth.update_user(str(user["uid"]), password=new_password, app=get_firebase_app())
    return RedirectResponse("/settings#profile", status_code=303)


@router.post("/settings/categories")
def add_category_route(
    name: str = Form(...),
    kind: str = Form(...),
    color: str = Form("#39ff88"),
    icon: str = Form("◇"),
    monthly_budget: Decimal = Form(0),
    user: dict = Depends(require_user),
):
    add_category(str(user["uid"]), user, name, kind, color, icon, monthly_budget)
    return RedirectResponse("/settings#categories", status_code=303)


@router.post("/settings/categories/{category_id}")
def update_category_route(
    category_id: str,
    name: str = Form(...),
    color: str = Form("#39ff88"),
    icon: str = Form("◇"),
    monthly_budget: Decimal = Form(0),
    user: dict = Depends(require_user),
):
    update_category(str(user["uid"]), user, category_id, name, color, icon, monthly_budget)
    return RedirectResponse("/settings#categories", status_code=303)


@router.post("/settings/recurring")
def add_recurring(
    name: str = Form(...),
    category_id: str | None = Form(None),
    amount: Decimal = Form(...),
    frequency: str = Form("monthly"),
    next_due: str = Form(""),
    note: str = Form(""),
    user: dict = Depends(require_user),
):
    category = next((item for item in get_categories(user, "expense") if item["id"] == category_id), None)
    store.create_record(
        str(user["uid"]),
        RECURRING,
        {
            "category_id": category_id or "",
            "category": category or {},
            "name": name.strip(),
            "amount": to_decimal(amount),
            "frequency": frequency,
            "next_due": optional_date(next_due),
            "status": "active",
            "note": note.strip(),
        },
    )
    return RedirectResponse("/recurring", status_code=303)


@router.post("/settings/recurring/{item_id}/delete")
def delete_recurring(item_id: str, user: dict = Depends(require_user)):
    store.delete_record(str(user["uid"]), RECURRING, item_id)
    return RedirectResponse("/recurring", status_code=303)


@router.post("/settings/wishlist")
def add_wishlist(
    name: str = Form(...),
    price: Decimal = Form(...),
    note: str = Form(""),
    user: dict = Depends(require_user),
):
    store.create_record(
        str(user["uid"]),
        WISHLIST,
        {
            "name": name.strip(),
            "price": to_decimal(price),
            "status": "wish",
            "note": note.strip(),
        },
    )
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/wishlist/{item_id}/delete")
def delete_wishlist(item_id: str, user: dict = Depends(require_user)):
    store.delete_record(str(user["uid"]), WISHLIST, item_id)
    return RedirectResponse("/settings", status_code=303)
