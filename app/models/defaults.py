from __future__ import annotations

from app.core.config import settings


EXPENSE_CATEGORIES = [
    {"id": "expense_food", "name": "Food", "kind": "expense", "color": "#39ff88", "icon": "☕", "monthly_budget": 8000},
    {"id": "expense_shopping", "name": "Shopping", "kind": "expense", "color": "#ff4fd8", "icon": "◆", "monthly_budget": 5000},
    {"id": "expense_fuel", "name": "Fuel", "kind": "expense", "color": "#33ccff", "icon": "⛽", "monthly_budget": 4500},
    {"id": "expense_bills", "name": "Bills", "kind": "expense", "color": "#ffe66d", "icon": "⚡", "monthly_budget": 7000},
    {"id": "expense_rent", "name": "Rent", "kind": "expense", "color": "#a782ff", "icon": "⌂", "monthly_budget": 12000},
    {"id": "expense_travel", "name": "Travel", "kind": "expense", "color": "#ff8a4c", "icon": "✈", "monthly_budget": 4000},
    {"id": "expense_health", "name": "Health", "kind": "expense", "color": "#ff5577", "icon": "+", "monthly_budget": 3500},
    {"id": "expense_other", "name": "Other", "kind": "expense", "color": "#8affc1", "icon": "◇", "monthly_budget": 2500},
]

INCOME_CATEGORIES = [
    {"id": "income_salary", "name": "Salary", "kind": "income", "color": "#39ff88", "icon": "₹", "monthly_budget": 0},
    {"id": "income_business", "name": "Business", "kind": "income", "color": "#33ccff", "icon": "▣", "monthly_budget": 0},
    {"id": "income_freelance", "name": "Freelance", "kind": "income", "color": "#ff4fd8", "icon": "✦", "monthly_budget": 0},
    {"id": "income_other", "name": "Other", "kind": "income", "color": "#ffe66d", "icon": "◇", "monthly_budget": 0},
]

DEFAULT_CATEGORIES = EXPENSE_CATEGORIES + INCOME_CATEGORIES

DEFAULT_PROFILE = {
    "username": "D OS User",
    "currency": settings.default_currency,
    "monthly_budget": 30000,
    "categories": DEFAULT_CATEGORIES,
    "has_seen_onboarding": False,
}

