from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.firebase.firebase import get_firestore_client
from app.firebase.schema import PROFILE, PROFILE_DOCUMENT, SETTINGS, SETTINGS_DOCUMENT, USERS
from app.models.defaults import DEFAULT_CATEGORIES, DEFAULT_PROFILE
from app.utils.formatting import slugify, to_decimal


def user_ref(uid: str):
    return get_firestore_client().collection(USERS).document(uid)


def profile_ref(uid: str):
    return user_ref(uid).collection(PROFILE).document(PROFILE_DOCUMENT)


def settings_ref(uid: str):
    return user_ref(uid).collection(SETTINGS).document(SETTINGS_DOCUMENT)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _profile_payload(uid: str, email: str, username: str) -> dict[str, Any]:
    timestamp = now_iso()
    payload = dict(DEFAULT_PROFILE)
    payload["userId"] = uid
    payload["uid"] = uid
    payload["email"] = email
    payload["username"] = username or DEFAULT_PROFILE["username"]
    payload["createdAt"] = timestamp
    payload["updatedAt"] = timestamp
    payload["categories"] = [dict(category) for category in DEFAULT_CATEGORIES]
    return payload


def _ensure_user_root(uid: str, email: str, username: str) -> None:
    timestamp = now_iso()
    user_ref(uid).set(
        {
            "userId": uid,
            "email": email,
            "username": username or "D OS User",
            "createdAt": timestamp,
            "updatedAt": timestamp,
        },
        merge=True,
    )


def _ensure_settings_document(uid: str) -> None:
    timestamp = now_iso()
    settings_ref(uid).set(
        {
            "userId": uid,
            "theme": "retro-crt",
            "currency": DEFAULT_PROFILE["currency"],
            "createdAt": timestamp,
            "updatedAt": timestamp,
        },
        merge=True,
    )


def ensure_user_profile(uid: str, email: str = "", username: str = "") -> dict[str, Any]:
    _ensure_user_root(uid, email, username)
    ref = profile_ref(uid)
    snapshot = ref.get()
    if not snapshot.exists:
        payload = _profile_payload(uid, email, username)
        ref.set(payload)
        _sync_budget_documents(uid, payload["categories"], payload["monthly_budget"])
        _ensure_settings_document(uid)
        return payload
    profile = snapshot.to_dict() or {}
    changed = False
    if not profile.get("userId"):
        profile["userId"] = uid
        changed = True
    if not profile.get("uid"):
        profile["uid"] = uid
        changed = True
    if email and profile.get("email") != email:
        profile["email"] = email
        changed = True
    if username and profile.get("username") in {"", None, "D OS User"}:
        profile["username"] = username
        changed = True
    categories = profile.get("categories") or []
    existing = {category.get("id") for category in categories}
    for category in DEFAULT_CATEGORIES:
        if category["id"] not in existing:
            categories.append(dict(category))
            changed = True
    profile["categories"] = categories
    profile.setdefault("currency", DEFAULT_PROFILE["currency"])
    profile.setdefault("monthly_budget", DEFAULT_PROFILE["monthly_budget"])
    if not profile.get("createdAt"):
        profile["createdAt"] = now_iso()
        changed = True
    if changed:
        profile["updatedAt"] = now_iso()
        ref.set(profile, merge=True)
        _sync_budget_documents(uid, categories, profile["monthly_budget"])
    _ensure_settings_document(uid)
    return profile


def get_user_profile(uid: str, email: str = "", username: str = "") -> dict[str, Any]:
    """Read the profile for an authenticated user without routine writes.

    Route guards call this on every protected request, so it must stay cheap:
    one profile document read in the normal case. New accounts are still seeded
    through ensure_user_profile during session creation, with a defensive
    fallback here for older sessions that predate that flow.
    """
    snapshot = profile_ref(uid).get()
    if not snapshot.exists:
        return ensure_user_profile(uid, email=email, username=username)

    profile = snapshot.to_dict() or {}
    profile.setdefault("uid", uid)
    profile.setdefault("userId", uid)
    profile.setdefault("email", email)
    profile.setdefault("username", username or "D OS User")
    profile.setdefault("currency", DEFAULT_PROFILE["currency"])
    profile.setdefault("monthly_budget", DEFAULT_PROFILE["monthly_budget"])
    profile.setdefault("categories", [dict(category) for category in DEFAULT_CATEGORIES])
    profile.setdefault("has_seen_onboarding", False)
    return profile


def update_profile(uid: str, username: str, currency: str) -> dict[str, Any]:
    ref = profile_ref(uid)
    payload = {
        "userId": uid,
        "username": username.strip() or "D OS User",
        "currency": (currency.strip() or "₹")[:8],
        "updatedAt": now_iso(),
    }
    ref.set(payload, merge=True)
    profile = ref.get().to_dict() or {}
    profile["uid"] = uid
    return profile


def get_categories(profile: dict[str, Any], kind: str | None = None) -> list[dict[str, Any]]:
    categories = [dict(category) for category in profile.get("categories", [])]
    if kind:
        categories = [category for category in categories if category.get("kind") == kind]
    return sorted(categories, key=lambda item: (item.get("kind", ""), item.get("name", "")))


def find_category(
    profile: dict[str, Any], category_id: str | None, kind: str | None = None
) -> dict[str, Any]:
    categories = get_categories(profile, kind)
    for category in categories:
        if category["id"] == category_id:
            return category
    return categories[0] if categories else dict(DEFAULT_CATEGORIES[-1])


def add_category(
    uid: str,
    profile: dict[str, Any],
    name: str,
    kind: str,
    color: str,
    icon: str,
    monthly_budget: object,
) -> None:
    categories = get_categories(profile)
    category_id = f"{kind}_{slugify(name)}"
    categories.append(
        {
            "id": category_id,
            "name": name.strip(),
            "kind": kind,
            "color": color or "#39ff88",
            "icon": (icon or "◇")[:8],
            "monthly_budget": float(to_decimal(monthly_budget)),
        }
    )
    profile_ref(uid).set({"categories": categories, "userId": uid, "updatedAt": now_iso()}, merge=True)
    _sync_budget_documents(uid, categories, profile.get("monthly_budget", 0))


def update_category(
    uid: str,
    profile: dict[str, Any],
    category_id: str,
    name: str,
    color: str,
    icon: str,
    monthly_budget: object,
) -> None:
    categories = get_categories(profile)
    for category in categories:
        if category["id"] == category_id:
            category["name"] = name.strip() or category["name"]
            category["color"] = color or category["color"]
            category["icon"] = (icon or category["icon"])[:8]
            category["monthly_budget"] = float(to_decimal(monthly_budget))
            break
    profile_ref(uid).set({"categories": categories, "userId": uid, "updatedAt": now_iso()}, merge=True)
    _sync_budget_documents(uid, categories, profile.get("monthly_budget", 0))


def update_monthly_budget(uid: str, monthly_budget: object) -> None:
    amount = float(to_decimal(monthly_budget))
    profile_ref(uid).set(
        {"monthly_budget": amount, "userId": uid, "updatedAt": now_iso()},
        merge=True,
    )
    get_firestore_client().collection(USERS).document(uid).collection("budgets").document(
        "monthly"
    ).set(
        {"amount": amount, "userId": uid, "createdAt": now_iso(), "updatedAt": now_iso()},
        merge=True,
    )


def _sync_budget_documents(
    uid: str, categories: list[dict[str, Any]], monthly_budget: object
) -> None:
    budgets = user_ref(uid).collection("budgets")
    timestamp = now_iso()
    budgets.document("monthly").set(
        {
            "amount": float(to_decimal(monthly_budget)),
            "userId": uid,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        },
        merge=True,
    )
    for category in categories:
        if category.get("kind") == "expense":
            budgets.document(str(category["id"])).set(
                {
                    "category_id": category["id"],
                    "category_name": category["name"],
                    "amount": float(to_decimal(category.get("monthly_budget"))),
                    "userId": uid,
                    "createdAt": timestamp,
                    "updatedAt": timestamp,
                },
                merge=True,
            )
