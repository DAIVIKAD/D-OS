from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


ZERO = Decimal("0")


def to_decimal(value: Any, default: Decimal = ZERO) -> Decimal:
    try:
        if value is None or value == "":
            return default
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return default


def as_float(value: Any) -> float:
    return float(to_decimal(value))


def optional_date(value: str | date | None) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        val_str = str(value).strip()
        if "T" in val_str:
            val_str = val_str.split("T")[0]
        elif " " in val_str:
            val_str = val_str.split(" ")[0]
        return date.fromisoformat(val_str)
    except Exception:
        return None


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return optional_date(value)
    return None


def date_key(value: Any) -> str:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else ""


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    return "_".join(part for part in cleaned.split("_") if part) or "item"

