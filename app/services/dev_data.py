from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from itertools import count
from typing import Any

from app.firebase.schema import (
    EXPENSES,
    GOALS,
    INCOME,
    INVESTMENTS,
    LEND_BORROW,
    RECURRING,
    REPORTS,
    SETTINGS,
    WISHLIST,
)
from app.models.defaults import DEFAULT_CATEGORIES
from app.utils.formatting import parse_date, to_decimal

DEV_USER_ID = "dev-user"
_ids = count(1000)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta(record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "id": record_id,
        "userId": DEV_USER_ID,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        **payload,
    }


def _category(category_id: str) -> dict[str, Any]:
    return next(
        (dict(category) for category in DEFAULT_CATEGORIES if category["id"] == category_id),
        dict(DEFAULT_CATEGORIES[-1]),
    )


def _seed() -> dict[str, list[dict[str, Any]]]:
    today = date.today()
    expenses = [
        _meta("exp_food_today", {"category_id": "expense_food", "category": _category("expense_food"), "amount": Decimal("480"), "date": today, "note": "Lunch and coffee", "payment_method": "UPI"}),
        _meta("exp_travel_today", {"category_id": "expense_travel", "category": _category("expense_travel"), "amount": Decimal("950"), "date": today, "note": "Metro recharge", "payment_method": "Card"}),
        _meta("exp_shop_yesterday", {"category_id": "expense_shopping", "category": _category("expense_shopping"), "amount": Decimal("2400"), "date": today - timedelta(days=1), "note": "Shoes", "payment_method": "UPI"}),
        _meta("exp_bills", {"category_id": "expense_bills", "category": _category("expense_bills"), "amount": Decimal("1850"), "date": today - timedelta(days=2), "note": "Internet bill", "payment_method": "AutoPay"}),
        _meta("exp_fuel", {"category_id": "expense_fuel", "category": _category("expense_fuel"), "amount": Decimal("3000"), "date": today - timedelta(days=4), "note": "Petrol", "payment_method": "Card"}),
        _meta("exp_rent", {"category_id": "expense_rent", "category": _category("expense_rent"), "amount": Decimal("15000"), "date": today.replace(day=2), "note": "Apartment rent", "payment_method": "Bank"}),
    ]
    income = [
        _meta("inc_salary", {"category_id": "income_salary", "category": _category("income_salary"), "amount": Decimal("85000"), "date": today.replace(day=1), "note": "Monthly salary", "payment_method": "Bank"}),
        _meta("inc_freelance", {"category_id": "income_freelance", "category": _category("income_freelance"), "amount": Decimal("12000"), "date": today - timedelta(days=5), "note": "Landing page work", "payment_method": "UPI"}),
    ]
    for months_back in range(1, 5):
        base = (today.replace(day=1) - timedelta(days=months_back * 28)).replace(day=1)
        income.append(_meta(f"inc_salary_{months_back}", {"category_id": "income_salary", "category": _category("income_salary"), "amount": Decimal("82000"), "date": base, "note": "Monthly salary", "payment_method": "Bank"}))
        expenses.extend(
            [
                _meta(f"exp_rent_{months_back}", {"category_id": "expense_rent", "category": _category("expense_rent"), "amount": Decimal("15000"), "date": base + timedelta(days=1), "note": "Apartment rent", "payment_method": "Bank"}),
                _meta(f"exp_food_{months_back}", {"category_id": "expense_food", "category": _category("expense_food"), "amount": Decimal("7200") + Decimal(months_back * 280), "date": base + timedelta(days=10), "note": "Groceries", "payment_method": "UPI"}),
                _meta(f"exp_shop_{months_back}", {"category_id": "expense_shopping", "category": _category("expense_shopping"), "amount": Decimal("3100") + Decimal(months_back * 250), "date": base + timedelta(days=16), "note": "Shopping", "payment_method": "Card"}),
            ]
        )
    return {
        EXPENSES: expenses,
        INCOME: income,
        GOALS: [
            _meta("goal_pc", {"name": "Gaming PC", "image": "/static/assets/goals/gaming-pc.svg", "target_amount": Decimal("140000"), "current_saved": Decimal("52000"), "target_date": today + timedelta(days=190), "status": "active"}),
            _meta("goal_emergency", {"name": "Emergency Fund", "image": "/static/assets/goals/emergency-fund.svg", "target_amount": Decimal("250000"), "current_saved": Decimal("96000"), "target_date": today + timedelta(days=365), "status": "active"}),
        ],
        "budgets": [
            _meta("monthly", {"amount": Decimal("45000")}),
            *[
                _meta(category["id"], {"category_id": category["id"], "category_name": category["name"], "amount": Decimal(str(category["monthly_budget"]))})
                for category in DEFAULT_CATEGORIES
                if category["kind"] == "expense"
            ],
        ],
        LEND_BORROW: [
            _meta("lend_aarav", {"direction": "lend", "person_name": "Aarav", "phone": "+91 98765 43210", "amount": Decimal("5000"), "due_date": today + timedelta(days=10), "status": "pending", "note": "Trip split"}),
            _meta("borrow_mira", {"direction": "borrow", "person_name": "Mira", "phone": "+91 99887 77665", "amount": Decimal("2200"), "due_date": today + timedelta(days=5), "status": "pending", "note": "Dinner payment"}),
        ],
        INVESTMENTS: [
            _meta("plan_index_sip", {"name": "Index SIP", "kind": "sip", "initial_amount": Decimal("25000"), "monthly_investment": Decimal("7000"), "interest_rate": Decimal("11"), "years": 8}),
        ],
        WISHLIST: [
            _meta("wish_phone", {"name": "Phone Upgrade", "price": Decimal("68000"), "image": "/static/assets/goals/phone.svg", "status": "wish", "note": "Wait for festival sale"}),
        ],
        RECURRING: [
            _meta("rec_netflix", {"name": "Netflix", "category_id": "expense_bills", "category": _category("expense_bills"), "amount": Decimal("649"), "frequency": "monthly", "next_due": today + timedelta(days=4), "status": "active", "note": "Entertainment"}),
            _meta("rec_electricity", {"name": "Electricity", "category_id": "expense_bills", "category": _category("expense_bills"), "amount": Decimal("2100"), "frequency": "monthly", "next_due": today + timedelta(days=8), "status": "active", "note": "Home"}),
        ],
        SETTINGS: [
            _meta("main", {"theme": "retro-crt", "currency": "₹"}),
        ],
        "custom_budgets": [
            _meta("custom_goa", {
                "name": "Goa Trip",
                "target_amount": Decimal("12000"),
                "spent_amount": Decimal("4500"),
                "expenses": [{"amount": 2500, "note": "Hotel Advance"}, {"amount": 2000, "note": "Flight Ticket"}],
            }),
        ],
        REPORTS: [],
    }


_collections = _seed()


def mock_user() -> dict[str, Any]:
    return {
        "uid": DEV_USER_ID,
        "userId": DEV_USER_ID,
        "email": "dev@dos.local",
        "username": "Development User",
        "currency": "₹",
        "monthly_budget": Decimal("45000"),
        "categories": deepcopy(DEFAULT_CATEGORIES),
        "devBypass": True,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }


def _copy(record: dict[str, Any]) -> dict[str, Any]:
    copied = deepcopy(record)
    for key in ("date", "target_date", "due_date", "next_due", "createdAt", "updatedAt"):
        parsed = parse_date(copied.get(key))
        if parsed:
            copied[key] = parsed
    for key in ("amount", "target_amount", "current_saved", "monthly_budget", "price"):
        if key in copied:
            copied[key] = to_decimal(copied[key])
    return copied


def list_collection(collection: str) -> list[dict[str, Any]]:
    return [_copy(record) for record in _collections.get(collection, [])]


def get_record(collection: str, record_id: str) -> dict[str, Any] | None:
    for record in _collections.get(collection, []):
        if record["id"] == record_id:
            return _copy(record)
    return None


def create_record(collection: str, data: dict[str, Any]) -> str:
    record_id = f"dev_{next(_ids)}"
    _collections.setdefault(collection, []).append(_meta(record_id, deepcopy(data)))
    return record_id


def set_record(collection: str, record_id: str, data: dict[str, Any]) -> None:
    records = _collections.setdefault(collection, [])
    for record in records:
        if record["id"] == record_id:
            record.update(deepcopy(data))
            record["userId"] = DEV_USER_ID
            record["updatedAt"] = now_iso()
            return
    records.append(_meta(record_id, deepcopy(data)))


def delete_record(collection: str, record_id: str) -> None:
    _collections[collection] = [
        record for record in _collections.get(collection, []) if record["id"] != record_id
    ]

