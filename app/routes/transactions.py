from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from app.core.templates import templates
from app.core.view import context, is_htmx
from app.firebase.auth import require_user
from app.services import firestore_service as store
from app.services.finance import as_float, to_decimal, transaction_query
from app.services.profile_service import find_category, get_categories
from app.utils.formatting import optional_date

router = APIRouter()


def _money_page(
    request: Request,
    user: dict,
    kind: str | None,
    page_title: str,
    search: str | None,
    category_id: str | None,
    start: str | None,
    end: str | None,
):
    rows = transaction_query(
        user,
        kind=kind,
        search=search,
        category_id=category_id,
        start=optional_date(start),
        end=optional_date(end),
    )
    totals = {
        "income": sum(to_decimal(tx.get("amount")) for tx in rows if tx.get("type") == "income"),
        "expense": sum(to_decimal(tx.get("amount")) for tx in rows if tx.get("type") == "expense"),
    }
    template = "partials/transaction_table.html" if is_htmx(request) else "pages/transactions.html"
    return templates.TemplateResponse(
        template,
        context(
            request,
            user,
            page_title=page_title,
            kind=kind,
            rows=rows,
            categories=get_categories(user, kind),
            all_categories=get_categories(user),
            totals=totals,
            filters={
                "search": search or "",
                "category_id": category_id or "",
                "start": start or "",
                "end": end or "",
            },
        ),
    )


@router.get("/transactions")
def transactions_alias(user: dict = Depends(require_user)):
    return RedirectResponse("/money", status_code=303)


@router.get("/money")
def money_page(
    request: Request,
    search: str | None = None,
    category_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user: dict = Depends(require_user),
):
    return _money_page(request, user, None, "Money", search, category_id, start, end)


@router.get("/income")
def income_page(
    request: Request,
    search: str | None = None,
    category_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user: dict = Depends(require_user),
):
    return _money_page(request, user, "income", "Income", search, category_id, start, end)


@router.get("/expenses")
def expenses_page(
    request: Request,
    search: str | None = None,
    category_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user: dict = Depends(require_user),
):
    return _money_page(request, user, "expense", "Expenses", search, category_id, start, end)


@router.post("/transactions")
def create_transaction(
    type: str = Form(...),
    category_id: str = Form(...),
    amount: Decimal = Form(...),
    date_value: str = Form(alias="date"),
    note: str = Form(""),
    payment_method: str = Form("Cash"),
    user: dict = Depends(require_user),
):
    category = find_category(user, category_id, type)
    store.create_transaction(
        str(user["uid"]),
        type,
        {
            "category_id": category["id"],
            "category": category,
            "amount": to_decimal(amount),
            "date": optional_date(date_value) or date.today(),
            "note": note.strip(),
            "payment_method": payment_method.strip() or "Cash",
        },
    )
    return RedirectResponse("/income" if type == "income" else "/expenses", status_code=303)


@router.post("/transactions/{transaction_id}/update")
def update_transaction(
    transaction_id: str,
    type: str = Form(...),
    category_id: str = Form(...),
    amount: Decimal = Form(...),
    date_value: str = Form(alias="date"),
    note: str = Form(""),
    payment_method: str = Form("Cash"),
    user: dict = Depends(require_user),
):
    category = find_category(user, category_id, type)
    store.update_transaction(
        str(user["uid"]),
        transaction_id,
        type,
        {
            "category_id": category["id"],
            "category": category,
            "amount": to_decimal(amount),
            "date": optional_date(date_value) or date.today(),
            "note": note.strip(),
            "payment_method": payment_method.strip() or "Cash",
        },
    )
    return RedirectResponse("/money", status_code=303)


@router.post("/transactions/{transaction_id}/delete")
def delete_transaction(transaction_id: str, user: dict = Depends(require_user)):
    store.delete_transaction(str(user["uid"]), transaction_id)
    return RedirectResponse("/money", status_code=303)


@router.get("/api/transactions")
def transactions_api(
    kind: str | None = Query(default=None),
    search: str | None = Query(default=None),
    user: dict = Depends(require_user),
):
    return [
        {
            "id": tx["id"],
            "type": tx["type"],
            "amount": as_float(tx.get("amount")),
            "date": tx["date"].isoformat() if hasattr(tx.get("date"), "isoformat") else tx.get("date"),
            "note": tx.get("note", ""),
            "payment_method": tx.get("payment_method", ""),
            "category": (tx.get("category") or {}).get("name"),
        }
        for tx in transaction_query(user, kind=kind, search=search)
    ]

