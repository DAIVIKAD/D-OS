from __future__ import annotations

from fastapi import Request


NAV_ITEMS = [
    ("Dashboard", "/", "⌁"),
    ("Ledger", "/money", "₹"),
    ("Goals", "/goals", "◎"),
    ("Analytics", "/visualize", "▥"),
    ("Budget", "/budget", "▤"),
    ("Lend & Borrow", "/lend-borrow", "⇄"),
    ("Reports", "/reports", "▧"),
]


def context(
    request: Request, user: dict[str, object] | None = None, **extra: object
) -> dict[str, object]:
    from app.services.profile_service import get_categories

    default_categories = get_categories(user) if user else []
    return {
        "request": request,
        "current_user": user,
        "nav_items": NAV_ITEMS,
        "active_path": request.url.path,
        "global_categories": default_categories,
        **extra,
    }


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"
