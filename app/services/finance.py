from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from math import ceil
from typing import Any

from app.firebase.schema import GOALS, INVESTMENTS
from app.services import firestore_service as store
from app.utils.formatting import as_float, parse_date, to_decimal

ZERO = Decimal("0")


def current_month_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    start = today.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def previous_month_range(today: date | None = None) -> tuple[date, date]:
    start, _ = current_month_range(today)
    previous_end = start
    previous_start = (start - timedelta(days=1)).replace(day=1)
    return previous_start, previous_end


def uid_of(user: dict[str, Any]) -> str:
    """Extract user ID from a user profile dict."""
    return str(user["uid"])


# Keep underscore aliases for backward compatibility
_uid = uid_of


def tx_date(tx: dict[str, Any]) -> date:
    """Extract and parse the date from a transaction dict."""
    return parse_date(tx.get("date")) or date.min


# Keep underscore alias for backward compatibility
_tx_date = tx_date


def _date_in_range(
    value: date, start: date | None = None, end: date | None = None, exact_day: date | None = None
) -> bool:
    if exact_day and value != exact_day:
        return False
    if start and value < start:
        return False
    if end and value >= end:
        return False
    return True


# ---------------------------------------------------------------------------
# Pre-fetched data helpers — fetch each collection ONCE per request
# ---------------------------------------------------------------------------

def prefetch_data(user: dict[str, Any], *, include_investments: bool = True) -> dict[str, Any]:
    """Fetch all Firestore collections for a user in one pass.

    Returns a dict with keys: transactions, goals, debts, recurring,
    investments.  Every downstream function should use these lists
    instead of calling store.list_* independently.
    """
    uid = uid_of(user)
    return {
        "transactions": store.list_transactions(uid),
        "goals": store.list_goals(uid),
        "debts": store.list_debts(uid),
        "recurring": store.list_recurring(uid),
        "investments": store.list_investments(uid) if include_investments else [],
    }


def _filter_transactions(
    rows: list[dict[str, Any]],
    kind: str | None = None,
) -> list[dict[str, Any]]:
    """Filter a pre-fetched transaction list by kind (income/expense)."""
    if kind is None:
        return rows
    return [row for row in rows if row.get("type") == kind]


def _sum_from_rows(
    rows: list[dict[str, Any]],
    kind: str,
    start: date | None = None,
    end: date | None = None,
    exact_day: date | None = None,
    category_id: str | None = None,
) -> Decimal:
    """Sum transaction amounts from a pre-fetched list — NO Firestore calls."""
    total = ZERO
    for tx_item in _filter_transactions(rows, kind):
        if category_id and tx_item.get("category_id") != category_id:
            continue
        if _date_in_range(tx_date(tx_item), start, end, exact_day):
            total += to_decimal(tx_item.get("amount"))
    return total


# Legacy function that still hits Firestore (used by non-dashboard pages)
def sum_transactions(
    user: dict[str, Any],
    kind: str,
    start: date | None = None,
    end: date | None = None,
    exact_day: date | None = None,
    category_id: str | None = None,
) -> Decimal:
    total = ZERO
    for tx_item in store.list_transactions(uid_of(user), kind=kind):
        if category_id and tx_item.get("category_id") != category_id:
            continue
        if _date_in_range(tx_date(tx_item), start, end, exact_day):
            total += to_decimal(tx_item.get("amount"))
    return total


def goal_metrics(goal: dict[str, Any]) -> dict[str, Any]:
    target = to_decimal(goal.get("target_amount"))
    saved = min(to_decimal(goal.get("current_saved")), target) if target else ZERO
    remaining = max(target - saved, ZERO)
    progress = (saved / target * Decimal("100")) if target else ZERO
    target_date = parse_date(goal.get("target_date"))
    daily = weekly = monthly = ZERO
    estimated_completion = "Set a target date"
    if target_date:
        days_left = max((target_date - date.today()).days, 1)
        daily = (remaining / Decimal(days_left)).quantize(Decimal("0.01"))
        weekly = (daily * Decimal("7")).quantize(Decimal("0.01"))
        monthly = (daily * Decimal("30")).quantize(Decimal("0.01"))
        estimated_completion = target_date.strftime("%d %b %Y")
    elif remaining == ZERO:
        estimated_completion = "Completed"
    return {
        "id": goal.get("id"),
        "name": goal.get("name", "Goal"),
        "image": goal.get("image", "/static/assets/goals/default.svg"),
        "target_amount": target,
        "current_saved": saved,
        "remaining": remaining,
        "target_date": target_date,
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "estimated_completion": estimated_completion,
        "progress": min(progress, Decimal("100")).quantize(Decimal("0.1")),
        "status": "completed" if remaining == ZERO else goal.get("status", "active"),
    }


def smart_tips(
    user: dict[str, Any],
    month_start: date | None = None,
    month_end: date | None = None,
    *,
    _rows: list[dict[str, Any]] | None = None,
    _goals: list[dict[str, Any]] | None = None,
    _recurring: list[dict[str, Any]] | None = None,
) -> list[str]:
    month_start, month_end = (
        month_start or current_month_range()[0],
        month_end or current_month_range()[1],
    )
    previous_start, previous_end = previous_month_range(month_start)
    tips: list[str] = []

    # Use pre-fetched rows or fall back to Firestore
    rows = _rows if _rows is not None else store.list_transactions(uid_of(user))

    expense = _sum_from_rows(rows, "expense", month_start, month_end)
    previous_expense = _sum_from_rows(rows, "expense", previous_start, previous_end)
    budget = to_decimal(user.get("monthly_budget"))
    if budget and expense >= budget * Decimal("0.9"):
        tips.append("Budget nearly exhausted. Freeze non-essential shopping for two days.")
    elif budget:
        remaining = budget - expense
        days_left = max((month_end - date.today()).days, 1)
        if remaining / Decimal(days_left) < Decimal("250"):
            tips.append("Daily spending room is tight. Keep cash expenses below today's limit.")

    if previous_expense and expense > previous_expense * Decimal("1.15"):
        tips.append("Spending increased from last month. Review top categories before the weekend.")

    category_totals: dict[str, Decimal] = defaultdict(Decimal)
    for tx_item in _filter_transactions(rows, "expense"):
        if _date_in_range(tx_date(tx_item), month_start, month_end):
            category = tx_item.get("category") or {}
            category_totals[str(category.get("name") or "Uncategorized")] += to_decimal(tx_item.get("amount"))

    categories = {
        category.get("name"): to_decimal(category.get("monthly_budget"))
        for category in user.get("categories", [])
        if category.get("kind") == "expense"
    }
    for name, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
        if categories.get(name) and total > categories[name]:
            tips.append(f"{name} crossed its category budget. Switch to a lower-cost option this week.")

    goals = _goals if _goals is not None else store.list_goals(uid_of(user))
    for goal in goals:
        metrics = goal_metrics(goal)
        if metrics["remaining"] and metrics["target_date"] and metrics["daily"] > ZERO:
            tips.append(f"Add {metrics['daily']} daily toward {goal.get('name', 'your goal')} to stay on schedule.")
            break

    recurring = _recurring if _recurring is not None else store.list_recurring(uid_of(user))
    for item in recurring[:2]:
        due = parse_date(item.get("next_due"))
        if due and due <= date.today() + timedelta(days=5) and item.get("status", "active") == "active":
            tips.append(f"{item.get('name', 'A recurring payment')} is due soon. Keep that amount aside now.")

    if not tips:
        tips.append("Money flow looks stable. Move a small surplus into your top goal today.")
    return tips[:6]


def smart_warning(
    user: dict[str, Any],
    *,
    _rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    month_start, month_end = current_month_range()
    rows = _rows if _rows is not None else store.list_transactions(uid_of(user))
    expense = _sum_from_rows(rows, "expense", month_start, month_end)
    budget = to_decimal(user.get("monthly_budget"))
    if not budget:
        return None
    remaining = max(budget - expense, ZERO)
    days_left = max((month_end - date.today()).days, 1)
    daily_room = remaining / Decimal(days_left)
    if remaining <= budget * Decimal("0.2") or daily_room < Decimal("350"):
        average_daily = expense / max(date.today().day, 1) if expense else Decimal("1")
        return {
            "title": "Budget Remaining",
            "amount": remaining,
            "estimate": f"{ceil(remaining / max(average_daily, Decimal('1')))} days remaining",
            "action": "Reduce Shopping.",
            "severity": "danger" if remaining <= budget * Decimal("0.1") else "warning",
        }
    return None


def dashboard_data(user: dict[str, Any], data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build dashboard summary.

    If *data* is provided (from ``prefetch_data``), all computation runs
    against in-memory lists — zero additional Firestore calls.
    """
    if data is None:
        data = prefetch_data(user)

    today = date.today()
    month_start, month_end = current_month_range(today)
    rows = data["transactions"]
    goals = data["goals"]
    debts = data["debts"]
    recurring = data["recurring"]

    today_expense = _sum_from_rows(rows, "expense", exact_day=today)
    today_income = _sum_from_rows(rows, "income", exact_day=today)
    monthly_expense = _sum_from_rows(rows, "expense", month_start, month_end)
    monthly_income = _sum_from_rows(rows, "income", month_start, month_end)
    remaining_budget = max(to_decimal(user.get("monthly_budget")) - monthly_expense, ZERO)
    active_goals = [goal for goal in goals if goal.get("status", "active") == "active"]
    receive = sum(to_decimal(item.get("amount")) for item in debts if item.get("direction") == "lend" and item.get("status") == "pending")
    pay = sum(to_decimal(item.get("amount")) for item in debts if item.get("direction") == "borrow" and item.get("status") == "pending")
    recent = rows[:8]
    tips = smart_tips(user, month_start, month_end, _rows=rows, _goals=goals, _recurring=recurring)
    return {
        "today_expense": today_expense,
        "today_income": today_income,
        "monthly_expense": monthly_expense,
        "monthly_income": monthly_income,
        "remaining_budget": remaining_budget,
        "savings": monthly_income - monthly_expense,
        "active_goals": len(active_goals),
        "money_to_receive": receive,
        "money_to_pay": pay,
        "recent_transactions": recent,
        "today_tip": tips[0],
        "tips": tips,
        "warning": smart_warning(user, _rows=rows),
        "goal_cards": [goal_metrics(goal) for goal in active_goals[:3]],
    }


def transaction_query(
    user: dict[str, Any],
    kind: str | None = None,
    search: str | None = None,
    category_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    rows = store.list_transactions(uid_of(user), kind=kind)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if category_id and row.get("category_id") != category_id:
            continue
        row_date = tx_date(row)
        if start and row_date < start:
            continue
        if end and row_date > end:
            continue
        filtered.append(row)
    if search:
        needle = search.lower()
        filtered = [
            row
            for row in filtered
            if needle in str(row.get("note", "")).lower()
            or needle in str(row.get("payment_method", "")).lower()
            or needle in str((row.get("category") or {}).get("name", "")).lower()
        ]
    return filtered


def chart_data(user: dict[str, Any], data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build chart datasets.

    If *data* is provided (from ``prefetch_data``), all computation runs
    against in-memory lists — zero additional Firestore calls.
    """
    if data is None:
        data = prefetch_data(user)

    rows = list(reversed(data["transactions"]))
    today = date.today()
    month_start, month_end = current_month_range(today)
    last_31 = today - timedelta(days=30)

    monthly: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"income": ZERO, "expense": ZERO})
    daily: dict[str, Decimal] = defaultdict(Decimal)
    weekly: dict[str, Decimal] = defaultdict(Decimal)
    category: dict[str, Decimal] = defaultdict(Decimal)
    weekdays: dict[str, Decimal] = defaultdict(Decimal)
    heatmap: dict[str, Decimal] = defaultdict(Decimal)

    for tx_item in rows:
        d = tx_date(tx_item)
        if d == date.min:
            continue
        month_key = d.strftime("%b %Y")
        raw_kind = str(tx_item.get("type", "")).lower()
        kind = "income" if raw_kind == "income" else "expense"
        monthly[month_key][kind] += to_decimal(tx_item.get("amount"))
        if month_start <= d < month_end and kind == "expense":
            label = str((tx_item.get("category") or {}).get("name") or "Uncategorized")
            category[label] += to_decimal(tx_item.get("amount"))
            weekdays[d.strftime("%a")] += to_decimal(tx_item.get("amount"))
        if d >= today - timedelta(days=6) and kind == "expense":
            daily[d.strftime("%d %b")] += to_decimal(tx_item.get("amount"))
        if d >= today - timedelta(days=27) and kind == "expense":
            week_key = f"W{((today - d).days // 7) + 1}"
            weekly[week_key] += to_decimal(tx_item.get("amount"))
        if d >= last_31 and kind == "expense":
            heatmap[d.isoformat()] += to_decimal(tx_item.get("amount"))

    all_time_category: dict[str, Decimal] = defaultdict(Decimal)
    for tx_item in rows:
        if str(tx_item.get("type", "")).lower() == "expense":
            cat_name = str((tx_item.get("category") or {}).get("name") or "Uncategorized")
            all_time_category[cat_name] += to_decimal(tx_item.get("amount"))

    month_items = list(monthly.items())[-8:]
    goals = data["goals"]
    debts = data["debts"]
    budget = to_decimal(user.get("monthly_budget"))

    # Compute income/expense from already-aggregated monthly dict for current month
    current_month_key = month_start.strftime("%b %Y")
    expense = monthly.get(current_month_key, {"expense": ZERO})["expense"]
    income = monthly.get(current_month_key, {"income": ZERO})["income"]
    savings = income - expense

    receive = sum(to_decimal(debt.get("amount")) for debt in debts if debt.get("direction") == "lend" and debt.get("status") == "pending")
    pay = sum(to_decimal(debt.get("amount")) for debt in debts if debt.get("direction") == "borrow" and debt.get("status") == "pending")
    net_worth = max(savings, ZERO) + sum(to_decimal(goal.get("current_saved")) for goal in goals) + receive - pay

    active_category = category if sum(category.values()) > ZERO else all_time_category
    category_sorted = sorted(active_category.items(), key=lambda item: item[1], reverse=True)
    cat_total = sum(active_category.values())

    palette = ["#66FF99", "#ff5577", "#33ccff", "#ffe66d", "#ff4fd8", "#9b5cff", "#4faf70", "#ff9966", "#66ccff", "#ffcc00"]
    category_list = []
    for i, (label, total) in enumerate(category_sorted):
        pct_val = (total / cat_total * Decimal("100")) if cat_total > ZERO else Decimal("0")
        category_list.append({
            "name": label,
            "amount": as_float(total),
            "pct": f"{pct_val:.1f}%",
            "color": palette[i % len(palette)],
        })

    month_labels = [label for label, _ in month_items]
    month_incomes = [as_float(values["income"]) for _, values in month_items]
    month_expenses = [as_float(values["expense"]) for _, values in month_items]
    
    # Savings calculation: Monthly Net Savings (Income - Expense) and Cumulative Savings
    savings_monthly = [as_float(values["income"] - values["expense"]) for _, values in month_items]
    running_savings = Decimal("0")
    savings_cumulative = []
    for _, values in month_items:
        running_savings += (values["income"] - values["expense"])
        savings_cumulative.append(as_float(running_savings))

    has_savings = len(month_items) > 0 and any(values["income"] > ZERO or values["expense"] > ZERO for _, values in month_items)
    has_expense_history = any(values["expense"] > ZERO for _, values in month_items)
    has_income_history = any(values["income"] > ZERO for _, values in month_items)
    has_flow_data = len(month_labels) > 0 and (has_income_history or has_expense_history)
    has_category_data = cat_total > ZERO and len(category_sorted) > 0

    has_budget = budget > ZERO
    spent_float = as_float(expense)
    budget_float = as_float(budget)
    remaining_float = as_float(max(budget - expense, ZERO))
    budget_usage_pct = min(round((spent_float / budget_float * 100), 1), 100.0) if has_budget else 0.0

    years = sorted({str(tx_date(tx_item).year) for tx_item in rows if tx_date(tx_item) != date.min})[-4:]
    all_rows = data["transactions"]

    return {
        "monthly_income_expense": {
            "labels": month_labels,
            "income": month_incomes,
            "expense": month_expenses,
            "has_data": has_flow_data,
            "datasets": [
                {
                    "label": "Income",
                    "data": month_incomes,
                    "backgroundColor": "#66FF99",
                    "borderColor": "#33CC66",
                    "borderWidth": 1.5,
                },
                {
                    "label": "Expense",
                    "data": month_expenses,
                    "backgroundColor": "#ff5577",
                    "borderColor": "#ff3355",
                    "borderWidth": 1.5,
                },
            ],
        },
        "monthly_spending": {
            "labels": month_labels,
            "income": month_incomes,
            "expense": month_expenses,
            "has_data": has_flow_data,
        },
        "weekly_spending": {
            "labels": list(reversed(sorted(weekly.keys()))),
            "values": [as_float(weekly[key]) for key in reversed(sorted(weekly.keys()))],
            "has_data": any(weekly.values()),
        },
        "daily_spending": {
            "labels": [(today - timedelta(days=offset)).strftime("%d %b") for offset in range(6, -1, -1)],
            "values": [as_float(daily[(today - timedelta(days=offset)).strftime("%d %b")]) for offset in range(6, -1, -1)],
            "has_data": any(daily.values()),
        },
        "category_pie": {
            "labels": [label for label, _ in category_sorted],
            "values": [as_float(total) for _, total in category_sorted],
            "total": as_float(cat_total),
            "category_list": category_list,
            "has_data": has_category_data,
            "datasets": [
                {
                    "label": "Categories",
                    "data": [as_float(total) for _, total in category_sorted],
                    "backgroundColor": [item["color"] for item in category_list],
                    "borderColor": "#020804",
                    "borderWidth": 2,
                }
            ],
        },
        "savings_trajectory": {
            "labels": month_labels,
            "values": savings_monthly,
            "cumulative": savings_cumulative,
            "has_data": has_savings,
            "datasets": [
                {
                    "label": "Monthly Net Savings",
                    "data": savings_monthly,
                    "borderColor": "#66FF99",
                    "backgroundColor": "rgba(102, 255, 153, 0.18)",
                    "borderWidth": 2.5,
                }
            ],
        },
        "budget_progress": {
            "has_budget": has_budget,
            "has_data": has_budget,
            "budget": budget_float,
            "spent": spent_float,
            "remaining": remaining_float,
            "progress": budget_usage_pct,
            "is_overbudget": bool(expense > budget and has_budget),
            "labels": ["Spent", "Remaining"] if has_budget else [],
            "values": [spent_float, remaining_float] if has_budget else [],
            "datasets": [
                {
                    "label": "Budget Usage",
                    "data": [spent_float, remaining_float] if has_budget else [],
                    "backgroundColor": ["#ff5577", "#66FF99"],
                    "borderColor": "#020804",
                    "borderWidth": 2,
                }
            ],
        },
        "savings_progress": {
            "labels": ["Savings", "Spent"],
            "values": [as_float(max(savings, ZERO)), as_float(expense)],
            "has_data": has_savings,
        },
        "income_vs_expense": {
            "labels": ["Income", "Expense"],
            "values": [as_float(income), as_float(expense)],
            "has_data": bool(income > ZERO or expense > ZERO),
        },
        "goal_progress": {
            "labels": [str(goal.get("name", "Goal")) for goal in goals],
            "values": [as_float(goal_metrics(goal)["progress"]) for goal in goals],
            "has_data": len(goals) > 0,
        },
        "cash_flow": {
            "labels": month_labels,
            "values": savings_monthly,
            "has_data": has_savings,
        },
        "cumulative_cash_flow": {
            "labels": month_labels,
            "values": savings_cumulative,
            "has_data": has_savings,
            "datasets": [
                {
                    "label": "Cumulative Balance",
                    "data": savings_cumulative,
                    "borderColor": "#33ccff",
                    "backgroundColor": "rgba(51, 204, 255, 0.15)",
                    "borderWidth": 2,
                }
            ],
        },
        "investment_growth": saved_investment_series(user, data=data),
        "lending_vs_borrowing": {
            "labels": ["Need To Receive", "Need To Pay"],
            "values": [as_float(receive), as_float(pay)],
            "has_data": bool(receive > ZERO or pay > ZERO),
        },
        "expense_heatmap": {
            "labels": [(last_31 + timedelta(days=offset)).strftime("%d %b") for offset in range(31)],
            "values": [as_float(heatmap[(last_31 + timedelta(days=offset)).isoformat()]) for offset in range(31)],
            "has_data": any(heatmap.values()),
        },
        "top_categories": {
            "labels": [label for label, _ in category_sorted[:6]],
            "values": [as_float(total) for _, total in category_sorted[:6]],
            "has_data": has_category_data,
        },
        "monthly_comparison": {
            "labels": [label for label, _ in month_items[-2:]],
            "values": [as_float(values["expense"]) for _, values in month_items[-2:]],
            "has_data": has_expense_history and len(month_items[-2:]) > 0,
        },
        "yearly_comparison": {
            "labels": years,
            "values": [
                as_float(
                    sum(
                        to_decimal(tx_item.get("amount"))
                        for tx_item in rows
                        if str(tx_date(tx_item).year) == year and tx_item.get("type") == "expense"
                    )
                )
                for year in years
            ],
            "has_data": any(tx_item.get("type") == "expense" for tx_item in rows),
        },
        "spending_by_weekday": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "values": [as_float(weekdays[key]) for key in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]],
            "has_data": any(weekdays.values()),
        },
        "net_worth": {"labels": ["Net Worth"], "values": [as_float(net_worth)]},
        "warnings": smart_tips(user, _rows=all_rows, _goals=goals, _recurring=data["recurring"]),
        "warning_popup": smart_warning(user, _rows=all_rows),
    }


def calculate_investment(
    kind: str,
    initial_amount: Decimal,
    monthly_investment: Decimal,
    interest_rate: Decimal,
    years: int,
) -> dict[str, Any]:
    initial = max(to_decimal(initial_amount), ZERO)
    monthly = max(to_decimal(monthly_investment), ZERO)
    rate = max(to_decimal(interest_rate), ZERO) / Decimal("100")
    years = max(int(years or 0), 1)
    months = years * 12
    monthly_rate = rate / Decimal("12")
    balance = initial
    series: list[dict[str, Any]] = []

    if kind == "fixed_deposit":
        for month in range(1, months + 1):
            balance += balance * monthly_rate
            if month % 12 == 0:
                series.append({"label": f"Y{month // 12}", "value": as_float(balance)})
        invested = initial
    else:
        for month in range(1, months + 1):
            if kind in {"sip", "recurring_deposit", "custom"}:
                balance += monthly
            balance += balance * monthly_rate
            if month % 12 == 0:
                series.append({"label": f"Y{month // 12}", "value": as_float(balance)})
        invested = initial + monthly * Decimal(months)

    final = balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    interest = (final - invested).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "kind": kind,
        "final_value": final,
        "interest_earned": max(interest, ZERO),
        "total_invested": invested.quantize(Decimal("0.01")),
        "series": series,
    }


def saved_investment_series(user: dict[str, Any], *, data: dict[str, Any] | None = None) -> dict[str, Any]:
    if data is not None:
        plans = data["investments"]
    else:
        plans = store.list_investments(uid_of(user))
    if not plans:
        projection = calculate_investment("sip", ZERO, Decimal("5000"), Decimal("10"), 5)
        return {
            "labels": [point["label"] for point in projection["series"]],
            "values": [point["value"] for point in projection["series"]],
        }
    max_years = max(int(plan.get("years", 1)) for plan in plans)
    totals = [Decimal("0") for _ in range(max_years)]
    for plan in plans:
        projection = calculate_investment(
            str(plan.get("kind", "sip")),
            to_decimal(plan.get("initial_amount")),
            to_decimal(plan.get("monthly_investment")),
            to_decimal(plan.get("interest_rate")),
            int(plan.get("years", 1)),
        )
        for idx, point in enumerate(projection["series"]):
            totals[idx] += to_decimal(point["value"])
    return {
        "labels": [f"Y{idx + 1}" for idx in range(max_years)],
        "values": [as_float(value) for value in totals],
    }


def search_everything(user: dict[str, Any], query: str) -> dict[str, list[dict[str, Any]]]:
    needle = (query or "").strip().lower()
    if not needle:
        return {"transactions": [], "goals": [], "debts": [], "recurring": []}
    transactions = [
        {
            "label": f"{str(tx_item.get('type', '')).title()} · {(tx_item.get('category') or {}).get('name', 'Uncategorized')}",
            "detail": tx_item.get("note") or tx_item.get("payment_method", ""),
            "amount": as_float(tx_item.get("amount")),
            "url": f"/money?search={needle}",
        }
        for tx_item in transaction_query(user, search=needle)[:8]
    ]
    goals = [
        {
            "label": goal.get("name", "Goal"),
            "detail": goal.get("status", "active"),
            "amount": as_float(goal.get("target_amount")),
            "url": "/goals",
        }
        for goal in store.list_goals(uid_of(user))
        if needle in str(goal.get("name", "")).lower()
    ][:8]
    debts = [
        {
            "label": debt.get("person_name", ""),
            "detail": debt.get("direction", ""),
            "amount": as_float(debt.get("amount")),
            "url": "/lend-borrow",
        }
        for debt in store.list_debts(uid_of(user))
        if needle in str(debt.get("person_name", "")).lower() or needle in str(debt.get("note", "")).lower()
    ][:8]
    recurring = [
        {
            "label": item.get("name", ""),
            "detail": item.get("frequency", ""),
            "amount": as_float(item.get("amount")),
            "url": "/recurring",
        }
        for item in store.list_recurring(uid_of(user))
        if needle in str(item.get("name", "")).lower()
    ][:8]
    return {
        "transactions": transactions,
        "goals": goals,
        "debts": debts,
        "recurring": recurring,
    }
