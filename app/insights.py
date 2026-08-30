from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.services import firestore_service as store
from app.services.finance import (
    current_month_range,
    previous_month_range,
    to_decimal,
    tx_date,
    uid_of,
    _sum_from_rows,
    _filter_transactions,
    ZERO,
)


def generate_smart_insights(
    user: dict[str, Any],
    *,
    _rows: list[dict[str, Any]] | None = None,
    _goals: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """
    Money Management Engine:
    Rule-based financial analyzer providing actionable tips, budget warnings, and goal shortcuts.
    Returns list of dicts: [{"type": "info"|"success"|"warning"|"tip", "title": str, "message": str}]

    If *_rows* and *_goals* are provided (pre-fetched data), no Firestore calls are made.
    """
    insights: list[dict[str, str]] = []
    today = date.today()
    month_start, month_end = current_month_range(today)
    prev_start, prev_end = previous_month_range(month_start)
    currency = str(user.get("currency", "₹"))

    # Use pre-fetched rows or fall back to Firestore
    rows = _rows if _rows is not None else store.list_transactions(uid_of(user))

    curr_income = _sum_from_rows(rows, "income", month_start, month_end)
    curr_expense = _sum_from_rows(rows, "expense", month_start, month_end)
    prev_expense = _sum_from_rows(rows, "expense", prev_start, prev_end)

    # 1. Monthly Expense Comparison
    if prev_expense > Decimal("0") and curr_expense > Decimal("0"):
        diff_pct = ((curr_expense - prev_expense) / prev_expense * Decimal("100")).quantize(Decimal("1"))
        if diff_pct > Decimal("10"):
            insights.append({
                "type": "warning",
                "title": "Expense Spike Alert",
                "message": f"Monthly spending increased by {diff_pct}% compared to last month."
            })
        elif diff_pct < Decimal("-5"):
            insights.append({
                "type": "success",
                "title": "Savings Growth",
                "message": f"Monthly spending decreased by {abs(diff_pct)}% compared to last month. Great pacing!"
            })

    # 2. Budget Health & Daily Spend Tip
    budget = to_decimal(user.get("monthly_budget"))
    days_in_month = max((month_end - month_start).days, 1)
    days_passed = max((today - month_start).days, 1)
    days_remaining = max(days_in_month - days_passed, 1)

    if budget > Decimal("0"):
        remaining_budget = budget - curr_expense
        if curr_expense > budget:
            insights.append({
                "type": "warning",
                "title": "Budget Exceeded",
                "message": f"You have exceeded your monthly budget of {currency}{budget:,.0f} by {currency}{curr_expense - budget:,.0f}."
            })
        else:
            daily_limit = remaining_budget / Decimal(days_remaining)
            if daily_limit > Decimal("0"):
                insights.append({
                    "type": "tip",
                    "title": "Money Management Tip: Daily Pace",
                    "message": f"Keep remaining daily expenses under {currency}{daily_limit:,.0f}/day to stay inside your monthly budget."
                })

    # 3. Income vs Expense Savings Rate Tip (50-30-20 Rule)
    if curr_income > Decimal("0"):
        savings = curr_income - curr_expense
        savings_rate = (savings / curr_income * Decimal("100")).quantize(Decimal("1"))
        if savings_rate < Decimal("20"):
            insights.append({
                "type": "warning",
                "title": "Savings Rate Warning",
                "message": f"Current monthly savings rate is {savings_rate}%. Target at least 20% savings for financial health."
            })
        else:
            insights.append({
                "type": "success",
                "title": "Solid Savings Rate",
                "message": f"You are saving {savings_rate}% of your income this month. Excellent discipline!"
            })

    # 4. Category Overspending Insights
    categories = user.get("categories", [])
    category_totals: dict[str, Decimal] = {}
    for tx_item in _filter_transactions(rows, "expense"):
        tx_d = tx_date(tx_item)
        if month_start <= tx_d < month_end:
            cat_name = (tx_item.get("category") or {}).get("name", "Uncategorized")
            category_totals[cat_name] = category_totals.get(cat_name, Decimal("0")) + to_decimal(tx_item.get("amount"))

    for cat in categories:
        if cat.get("kind") == "expense":
            c_name = cat.get("name")
            c_budget = to_decimal(cat.get("monthly_budget"))
            c_spent = category_totals.get(c_name, Decimal("0"))
            if c_budget > Decimal("0") and c_spent > c_budget:
                insights.append({
                    "type": "warning",
                    "title": f"{c_name} Over Budget",
                    "message": f"{c_name} spending ({currency}{c_spent:,.0f}) exceeded target category budget ({currency}{c_budget:,.0f})."
                })

    # 5. Goal Acceleration Tip
    goals = _goals if _goals is not None else store.list_goals(uid_of(user))
    for goal in goals:
        target = to_decimal(goal.get("target_amount"))
        saved = to_decimal(goal.get("current_saved"))
        rem = target - saved
        if rem > Decimal("0") and goal.get("status", "active") == "active":
            target_d = goal.get("target_date")
            if target_d:
                t_date = parse_date_val(target_d)
                if t_date and t_date > today:
                    days_rem = (t_date - today).days
                    current_daily = rem / Decimal(max(days_rem, 1))
                    boost_daily = current_daily + Decimal("50")
                    new_days = int(rem / boost_daily)
                    days_saved = days_rem - new_days
                    if days_saved > 2:
                        insights.append({
                            "type": "tip",
                            "title": f"Goal Shortcut: {goal.get('name')}",
                            "message": f"Saving an extra {currency}50/day reaches '{goal.get('name')}' {days_saved} days earlier!"
                        })
                        break

    # Fallback default insight if list is empty
    if not insights:
        insights.append({
            "type": "info",
            "title": "System Nominal",
            "message": "All financial parameters are within normal operating bounds. Keep tracking!"
        })

    return insights[:6]


def parse_date_val(val: Any) -> date | None:
    if isinstance(val, date):
        return val
    if isinstance(val, str) and val:
        try:
            return date.fromisoformat(val[:10])
        except Exception:
            pass
    return None
