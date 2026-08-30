from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import require_user
from app.firebase.schema import LEND_BORROW
from app.services import firestore_service as store
from app.services.finance import to_decimal
from app.utils.formatting import optional_date

router = APIRouter()


@router.get("/lend-borrow")
def lend_borrow_page(request: Request, user: dict = Depends(require_user)):
    debts = store.list_debts(str(user["uid"]))
    receive = sum(to_decimal(item.get("amount")) for item in debts if item.get("direction") == "lend" and item.get("status") == "pending")
    pay = sum(to_decimal(item.get("amount")) for item in debts if item.get("direction") == "borrow" and item.get("status") == "pending")
    return templates.TemplateResponse(
        "pages/lend_borrow.html",
        context(request, user, page_title="Lend & Borrow", debts=debts, receive=receive, pay=pay),
    )


@router.post("/lend-borrow")
def create_debt(
    direction: str = Form(...),
    person_name: str = Form(...),
    phone: str = Form(""),
    amount: Decimal = Form(...),
    due_date: str = Form(""),
    status: str = Form("pending"),
    note: str = Form(""),
    user: dict = Depends(require_user),
):
    store.create_record(
        str(user["uid"]),
        LEND_BORROW,
        {
            "direction": direction,
            "person_name": person_name.strip(),
            "phone": phone.strip(),
            "amount": to_decimal(amount),
            "due_date": optional_date(due_date),
            "status": status,
            "note": note.strip(),
        },
    )
    return RedirectResponse("/lend-borrow", status_code=303)


@router.post("/lend-borrow/{debt_id}/status")
def update_debt_status(
    debt_id: str,
    status: str = Form(...),
    user: dict = Depends(require_user),
):
    store.set_record(str(user["uid"]), LEND_BORROW, debt_id, {"status": status})
    return RedirectResponse("/lend-borrow", status_code=303)


@router.post("/lend-borrow/{debt_id}/delete")
def delete_debt(debt_id: str, user: dict = Depends(require_user)):
    store.delete_record(str(user["uid"]), LEND_BORROW, debt_id)
    return RedirectResponse("/lend-borrow", status_code=303)

