from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="templates")


def money(value: object, currency: str = "₹") -> str:
    try:
        amount = Decimal(str(value or 0))
    except Exception:
        amount = Decimal("0")
    return f"{currency}{amount:,.2f}"


def compact_money(value: object, currency: str = "₹") -> str:
    try:
        amount = Decimal(str(value or 0))
    except Exception:
        amount = Decimal("0")
    abs_amount = abs(amount)
    if abs_amount >= Decimal("10000000"):
        return f"{currency}{amount / Decimal('10000000'):.2f}Cr"
    if abs_amount >= Decimal("100000"):
        return f"{currency}{amount / Decimal('100000'):.2f}L"
    if abs_amount >= Decimal("1000"):
        return f"{currency}{amount / Decimal('1000'):.1f}K"
    return f"{currency}{amount:.0f}"


def format_date(value: object) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        return value.date().strftime("%d %b %Y")
    if isinstance(value, date):
        return value.strftime("%d %b %Y")
    try:
        from app.utils.formatting import parse_date
        parsed = parse_date(value)
        if parsed:
            return parsed.strftime("%d %b %Y")
    except Exception:
        pass
    return str(value)


def pct(value: object) -> str:
    try:
        number = Decimal(str(value or 0))
    except Exception:
        number = Decimal("0")
    return f"{number:.1f}%"


templates.env.filters["money"] = money
templates.env.filters["compact_money"] = compact_money
templates.env.filters["format_date"] = format_date
templates.env.filters["pct"] = pct

