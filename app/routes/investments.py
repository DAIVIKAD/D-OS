from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.core.templates import templates
from app.core.view import context, is_htmx
from app.firebase.auth import require_user
from app.firebase.schema import INVESTMENTS
from app.services import firestore_service as store
from app.services.finance import as_float, calculate_investment, to_decimal

router = APIRouter()


@router.get("/investment")
def investment_page(request: Request, user: dict = Depends(require_user)):
    plans = store.list_investments(str(user["uid"]))
    sample = calculate_investment("sip", Decimal("10000"), Decimal("5000"), Decimal("10"), 5)
    return templates.TemplateResponse(
        "pages/investment.html",
        context(request, user, page_title="Investment", plans=plans, result=sample),
    )


@router.post("/investment/calculate")
def calculate_page(
    request: Request,
    kind: str = Form(...),
    initial_amount: Decimal = Form(0),
    monthly_investment: Decimal = Form(0),
    interest_rate: Decimal = Form(...),
    years: int = Form(...),
    user: dict = Depends(require_user),
):
    result = calculate_investment(kind, initial_amount, monthly_investment, interest_rate, years)
    if is_htmx(request):
        return templates.TemplateResponse(
            "partials/investment_projection.html",
            context(request, user, result=result),
        )
    return templates.TemplateResponse(
        "pages/investment.html",
        context(
            request,
            user,
            page_title="Investment",
            plans=store.list_investments(str(user["uid"])),
            result=result,
        ),
    )


@router.post("/investment/plans")
def save_plan(
    name: str = Form(...),
    kind: str = Form(...),
    initial_amount: Decimal = Form(0),
    monthly_investment: Decimal = Form(0),
    interest_rate: Decimal = Form(...),
    years: int = Form(...),
    user: dict = Depends(require_user),
):
    store.create_record(
        str(user["uid"]),
        INVESTMENTS,
        {
            "name": name.strip(),
            "kind": kind,
            "initial_amount": to_decimal(initial_amount),
            "monthly_investment": to_decimal(monthly_investment),
            "interest_rate": to_decimal(interest_rate),
            "years": max(years, 1),
        },
    )
    return RedirectResponse("/investment", status_code=303)


@router.post("/investment/plans/{plan_id}/delete")
def delete_plan(plan_id: str, user: dict = Depends(require_user)):
    store.delete_record(str(user["uid"]), INVESTMENTS, plan_id)
    return RedirectResponse("/investment", status_code=303)


@router.post("/api/investment/calculate")
def calculate_api(
    kind: str = Form(...),
    initial_amount: Decimal = Form(0),
    monthly_investment: Decimal = Form(0),
    interest_rate: Decimal = Form(...),
    years: int = Form(...),
    user: dict = Depends(require_user),
):
    result = calculate_investment(kind, initial_amount, monthly_investment, interest_rate, years)
    return {
        "final_value": as_float(result["final_value"]),
        "interest_earned": as_float(result["interest_earned"]),
        "total_invested": as_float(result["total_invested"]),
        "series": result["series"],
    }
