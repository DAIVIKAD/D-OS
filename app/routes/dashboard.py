from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import require_user
from app.insights import generate_smart_insights
from app.services.finance import as_float, chart_data, dashboard_data, prefetch_data

router = APIRouter()


@router.get("/")
def dashboard(request: Request, user: dict = Depends(require_user)):
    data = prefetch_data(user, include_investments=False)
    dash = dashboard_data(user, data)
    insights = generate_smart_insights(
        user, _rows=data["transactions"], _goals=data["goals"]
    )
    charts = {
        "income_vs_expense": {
            "labels": ["Income", "Expense"],
            "values": [
                as_float(dash["monthly_income"]),
                as_float(dash["monthly_expense"]),
            ],
        }
    }
    return templates.TemplateResponse(
        "pages/dashboard.html",
        context(request, user, dashboard=dash, charts=charts, smart_insights=insights, page_title="Dashboard"),
    )


@router.get("/visualize")
def visualize(request: Request, user: dict = Depends(require_user)):
    data = prefetch_data(user)
    charts = chart_data(user, data)
    insights = generate_smart_insights(
        user, _rows=data["transactions"], _goals=data["goals"]
    )
    return templates.TemplateResponse(
        "pages/visualize.html",
        context(request, user, charts=charts, smart_insights=insights, page_title="Analytics"),
    )


@router.get("/api/dashboard")
def dashboard_api(user: dict = Depends(require_user)):
    data = prefetch_data(user)
    dash = dashboard_data(user, data)
    return {
        "available_balance": as_float(dash["available_balance"]),
        "total_income": as_float(dash["total_income"]),
        "total_expense": as_float(dash["total_expense"]),
        "today_expense": as_float(dash["today_expense"]),
        "today_income": as_float(dash["today_income"]),
        "monthly_expense": as_float(dash["monthly_expense"]),
        "monthly_income": as_float(dash["monthly_income"]),
        "remaining_budget": as_float(dash["remaining_budget"]),
        "savings": as_float(dash["savings"]),
        "active_goals": dash["active_goals"],
        "money_to_receive": as_float(dash["money_to_receive"]),
        "money_to_pay": as_float(dash["money_to_pay"]),
        "today_tip": dash["today_tip"],
        "warning": dash["warning"],
    }


@router.get("/api/visualizations")
def visualizations_api(user: dict = Depends(require_user)):
    data = prefetch_data(user)
    return chart_data(user, data)


@router.get("/health")
def health():
    return {"status": "ok", "service": "D-OS"}
