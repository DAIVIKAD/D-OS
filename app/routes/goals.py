from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import require_user
from app.firebase.schema import GOALS, WISHLIST
from app.services import firestore_service as store
from app.services.finance import as_float, goal_metrics, to_decimal
from app.utils.formatting import optional_date

from app.utils.goal_icons import get_goal_svg

router = APIRouter()


def _enhance_goal(goal_dict: dict) -> dict:
    metrics = goal_metrics(goal_dict)
    metrics["svg_icon"] = get_goal_svg(metrics.get("name", ""))
    return metrics


@router.get("/goals")
def goals_page(request: Request, user: dict = Depends(require_user)):
    goals = store.list_goals(str(user["uid"]))
    return templates.TemplateResponse(
        "pages/goals.html",
        context(request, user, page_title="Goals", goals=[_enhance_goal(goal) for goal in goals]),
    )


@router.post("/goals")
def create_goal(
    name: str = Form(...),
    target_amount: Decimal = Form(...),
    current_saved: Decimal = Form(0),
    target_date: str = Form(""),
    image: str = Form("/static/assets/goals/default.svg"),
    user: dict = Depends(require_user),
):
    store.create_record(
        str(user["uid"]),
        GOALS,
        {
            "name": name.strip(),
            "image": image or "/static/assets/goals/default.svg",
            "target_amount": to_decimal(target_amount),
            "current_saved": to_decimal(current_saved),
            "target_date": optional_date(target_date),
            "status": "active",
        },
    )
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/update")
def update_goal(
    goal_id: str,
    name: str = Form(...),
    target_amount: Decimal = Form(...),
    current_saved: Decimal = Form(...),
    target_date: str = Form(""),
    status: str = Form("active"),
    image: str = Form("/static/assets/goals/default.svg"),
    user: dict = Depends(require_user),
):
    store.set_record(
        str(user["uid"]),
        GOALS,
        goal_id,
        {
            "name": name.strip(),
            "target_amount": to_decimal(target_amount),
            "current_saved": to_decimal(current_saved),
            "target_date": optional_date(target_date),
            "status": status,
            "image": image or "/static/assets/goals/default.svg",
        },
    )
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/add-money")
def add_goal_money(
    goal_id: str,
    amount: Decimal = Form(...),
    user: dict = Depends(require_user),
):
    goal = store.get_record(str(user["uid"]), GOALS, goal_id)
    if goal:
        current_saved = to_decimal(goal.get("current_saved")) + to_decimal(amount)
        status = "completed" if current_saved >= to_decimal(goal.get("target_amount")) else goal.get("status", "active")
        store.set_record(str(user["uid"]), GOALS, goal_id, {"current_saved": current_saved, "status": status})
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/delete")
def delete_goal(goal_id: str, user: dict = Depends(require_user)):
    store.delete_record(str(user["uid"]), GOALS, goal_id)
    return RedirectResponse("/goals", status_code=303)


@router.post("/wishlist/{item_id}/convert-to-goal")
def convert_wishlist_to_goal(
    item_id: str,
    target_date: str = Form(""),
    user: dict = Depends(require_user),
):
    uid = str(user["uid"])
    item = store.get_record(uid, WISHLIST, item_id)
    if item and not item.get("converted_goal_id"):
        goal_id = store.create_record(
            uid,
            GOALS,
            {
                "name": item.get("name", "Wishlist Goal"),
                "image": item.get("image") or "/static/assets/goals/default.svg",
                "target_amount": to_decimal(item.get("price")),
                "current_saved": Decimal("0"),
                "target_date": optional_date(target_date),
                "status": "active",
            },
        )
        store.set_record(uid, WISHLIST, item_id, {"converted_goal_id": goal_id, "status": "converted"})
    return RedirectResponse("/goals", status_code=303)


@router.get("/api/goals")
def goals_api(user: dict = Depends(require_user)):
    return [
        {
            **metrics,
            "target_amount": as_float(metrics["target_amount"]),
            "current_saved": as_float(metrics["current_saved"]),
            "remaining": as_float(metrics["remaining"]),
            "daily": as_float(metrics["daily"]),
            "weekly": as_float(metrics["weekly"]),
            "monthly": as_float(metrics["monthly"]),
            "progress": as_float(metrics["progress"]),
            "target_date": metrics["target_date"].isoformat() if metrics["target_date"] else None,
        }
        for metrics in [goal_metrics(goal) for goal in store.list_goals(str(user["uid"]))]
    ]

