from __future__ import annotations

import secrets
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import require_user
from app.firebase.schema import CUSTOM_BUDGETS
from app.services import firestore_service as store
from app.services.finance import current_month_range, to_decimal, tx_date
from app.services.profile_service import get_categories, update_category, update_monthly_budget

router = APIRouter()


def _format_custom_budget(item: dict) -> dict:
    target = to_decimal(item.get("target_amount"))
    expenses = item.get("expenses", [])
    if expenses:
        spent = sum(to_decimal(e.get("amount", 0)) for e in expenses)
    else:
        spent = to_decimal(item.get("spent_amount"))
    remaining = max(target - spent, Decimal("0"))
    progress = (
        min((spent / target * Decimal("100")), Decimal("100")).quantize(Decimal("0.1"))
        if target > 0
        else Decimal("0")
    )
    status = "OVER" if spent > target else "ACTIVE"

    formatted_expenses = []
    for idx, exp in enumerate(expenses):
        exp_id = str(exp.get("id") or f"exp_{idx}")
        exp_amt = to_decimal(exp.get("amount", 0))
        formatted_expenses.append({
            "id": exp_id,
            "amount": exp_amt,
            "note": exp.get("note", "Expense"),
            "date": exp.get("date", ""),
        })

    return {
        "id": item.get("id"),
        "name": item.get("name", "Custom Event Budget"),
        "target_amount": target,
        "spent_amount": spent,
        "remaining": remaining,
        "progress": progress,
        "status": status,
        "expenses": formatted_expenses,
    }


@router.get("/budget")
def budget_page(
    request: Request,
    view: str = "monthly",
    user: dict = Depends(require_user),
):
    uid = str(user["uid"])
    categories = get_categories(user, "expense")
    month_start, month_end = current_month_range()
    expense_rows = store.list_transactions(uid, kind="expense")
    budget = to_decimal(user.get("monthly_budget"))
    spent = sum(
        to_decimal(row.get("amount"))
        for row in expense_rows
        if month_start <= tx_date(row) < month_end
    )
    remaining = max(budget - spent, Decimal("0"))
    daily_limit = remaining / Decimal("30") if remaining else Decimal("0")
    health = "GOOD" if spent < budget * Decimal("0.7") else "WATCH" if spent < budget else "OVER"

    raw_custom = store.list_custom_budgets(uid)
    custom_budgets = [_format_custom_budget(item) for item in raw_custom]
    current_view = view or request.query_params.get("view", "monthly")

    return templates.TemplateResponse(
        "pages/budget.html",
        context(
            request,
            user,
            page_title="Budget",
            categories=categories,
            spent=spent,
            remaining=remaining,
            daily_limit=daily_limit,
            health=health,
            custom_budgets=custom_budgets,
            view=current_view,
        ),
    )


@router.post("/budget/monthly")
def update_monthly_budget_route(
    monthly_budget: Decimal = Form(...),
    user: dict = Depends(require_user),
):
    update_monthly_budget(str(user["uid"]), monthly_budget)
    return RedirectResponse("/budget", status_code=303)


@router.post("/budget/category/{category_id}")
def update_category_budget(
    category_id: str,
    monthly_budget: Decimal = Form(...),
    user: dict = Depends(require_user),
):
    category = next((item for item in get_categories(user) if item["id"] == category_id), None)
    if category:
        update_category(
            str(user["uid"]),
            user,
            category_id,
            category["name"],
            category["color"],
            category["icon"],
            monthly_budget,
        )
    return RedirectResponse("/budget", status_code=303)


@router.post("/budget/custom")
def create_custom_budget(
    name: str = Form(...),
    target_amount: Decimal = Form(...),
    user: dict = Depends(require_user),
):
    uid = str(user["uid"])
    clean_name = name.strip()
    target = max(to_decimal(target_amount), Decimal("0"))
    if not clean_name:
        return RedirectResponse("/budget?view=custom", status_code=303)

    store.create_record(
        uid,
        CUSTOM_BUDGETS,
        {
            "name": clean_name,
            "target_amount": target,
            "spent_amount": Decimal("0"),
            "expenses": [],
        },
    )
    return RedirectResponse("/budget?view=custom", status_code=303)


@router.post("/budget/custom/{budget_id}/expense")
def add_custom_budget_expense(
    budget_id: str,
    amount: Decimal = Form(...),
    note: str = Form(""),
    user: dict = Depends(require_user),
):
    uid = str(user["uid"])
    budget_item = store.get_record(uid, CUSTOM_BUDGETS, budget_id)
    if budget_item:
        exp_amount = max(to_decimal(amount), Decimal("0"))
        if exp_amount <= 0:
            return RedirectResponse("/budget?view=custom", status_code=303)

        expenses_list = list(budget_item.get("expenses") or [])
        expense_id = f"exp_{secrets.token_hex(4)}"
        clean_note = note.strip() or "Expense"
        expenses_list.append({
            "id": expense_id,
            "amount": float(exp_amount),
            "note": clean_note,
            "date": date.today().isoformat(),
        })
        new_spent = sum(to_decimal(e.get("amount", 0)) for e in expenses_list)

        store.set_record(
            uid,
            CUSTOM_BUDGETS,
            budget_id,
            {"spent_amount": new_spent, "expenses": expenses_list},
        )
    return RedirectResponse("/budget?view=custom", status_code=303)


@router.post("/budget/custom/{budget_id}/expense/{expense_id}/update")
def update_custom_budget_expense(
    budget_id: str,
    expense_id: str,
    amount: Decimal = Form(...),
    note: str = Form(""),
    user: dict = Depends(require_user),
):
    uid = str(user["uid"])
    budget_item = store.get_record(uid, CUSTOM_BUDGETS, budget_id)
    if budget_item:
        exp_amount = max(to_decimal(amount), Decimal("0"))
        expenses_list = list(budget_item.get("expenses") or [])
        for exp in expenses_list:
            if str(exp.get("id")) == expense_id:
                exp["amount"] = float(exp_amount)
                if note.strip():
                    exp["note"] = note.strip()
                break
        new_spent = sum(to_decimal(e.get("amount", 0)) for e in expenses_list)
        store.set_record(
            uid,
            CUSTOM_BUDGETS,
            budget_id,
            {"spent_amount": new_spent, "expenses": expenses_list},
        )
    return RedirectResponse("/budget?view=custom", status_code=303)


@router.post("/budget/custom/{budget_id}/expense/{expense_id}/delete")
def delete_custom_budget_expense(
    budget_id: str,
    expense_id: str,
    user: dict = Depends(require_user),
):
    uid = str(user["uid"])
    budget_item = store.get_record(uid, CUSTOM_BUDGETS, budget_id)
    if budget_item:
        expenses_list = [
            e for e in (budget_item.get("expenses") or [])
            if str(e.get("id")) != expense_id
        ]
        new_spent = sum(to_decimal(e.get("amount", 0)) for e in expenses_list)
        store.set_record(
            uid,
            CUSTOM_BUDGETS,
            budget_id,
            {"spent_amount": new_spent, "expenses": expenses_list},
        )
    return RedirectResponse("/budget?view=custom", status_code=303)


@router.post("/budget/custom/{budget_id}/delete")
def delete_custom_budget(budget_id: str, user: dict = Depends(require_user)):
    store.delete_record(str(user["uid"]), CUSTOM_BUDGETS, budget_id)
    return RedirectResponse("/budget?view=custom", status_code=303)
