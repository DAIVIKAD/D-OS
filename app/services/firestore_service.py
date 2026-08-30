from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.firebase.firebase import get_firestore_client
from app.firebase.schema import (
    EXPENSES,
    GOALS,
    INCOME,
    INVESTMENTS,
    LEND_BORROW,
    RECURRING,
    REPORTS,
    USERS,
    WISHLIST,
)
from app.utils.formatting import parse_date, to_decimal


COLLECTION_FOR_KIND = {"expense": EXPENSES, "income": INCOME}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def user_document(uid: str):
    return get_firestore_client().collection(USERS).document(uid)


def user_collection(uid: str, collection: str):
    return user_document(uid).collection(collection)


def clean_for_firestore(data: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, Decimal):
            cleaned[key] = float(value)
        elif isinstance(value, date):
            cleaned[key] = value.isoformat()
        else:
            cleaned[key] = value
    return cleaned


def hydrate_record(doc: Any, record_type: str | None = None) -> dict[str, Any]:
    data = doc.to_dict() or {}
    data["id"] = doc.id
    if record_type:
        data["type"] = record_type
    for key in ("amount", "target_amount", "current_saved", "monthly_budget", "price"):
        if key in data:
            data[key] = to_decimal(data[key])
    for key in (
        "date",
        "target_date",
        "due_date",
        "next_due",
        "createdAt",
        "updatedAt",
    ):
        if key in data:
            parsed = parse_date(data[key])
            data[key] = parsed if parsed else data[key]
    return data


def list_collection(uid: str, collection: str) -> list[dict[str, Any]]:
    return [hydrate_record(doc) for doc in user_collection(uid, collection).stream()]


def create_record(uid: str, collection: str, data: dict[str, Any]) -> str:
    timestamp = now_iso()
    payload = clean_for_firestore(
        {**data, "userId": uid, "createdAt": timestamp, "updatedAt": timestamp}
    )
    ref = user_collection(uid, collection).document()
    ref.set(payload)
    return ref.id


def set_record(uid: str, collection: str, record_id: str, data: dict[str, Any]) -> None:
    payload = clean_for_firestore({**data, "userId": uid, "updatedAt": now_iso()})
    user_collection(uid, collection).document(record_id).set(payload, merge=True)


def delete_record(uid: str, collection: str, record_id: str) -> None:
    user_collection(uid, collection).document(record_id).delete()


def get_record(uid: str, collection: str, record_id: str) -> dict[str, Any] | None:
    snapshot = user_collection(uid, collection).document(record_id).get()
    if not snapshot.exists:
        return None
    return hydrate_record(snapshot)


def list_transactions(uid: str, kind: str | None = None) -> list[dict[str, Any]]:
    kinds = [kind] if kind in COLLECTION_FOR_KIND else ["income", "expense"]
    rows: list[dict[str, Any]] = []
    for item_kind in kinds:
        collection = COLLECTION_FOR_KIND[item_kind]
        collection_rows = [
            hydrate_record(doc)
            for doc in user_collection(uid, collection).stream()
        ]
        for row in collection_rows:
            row["type"] = item_kind
            rows.append(row)
    return sorted(rows, key=lambda row: (row.get("date") or date.min, row.get("id", "")), reverse=True)


def get_transaction(uid: str, transaction_id: str) -> tuple[str, dict[str, Any]] | None:
    for kind, collection in COLLECTION_FOR_KIND.items():
        record = get_record(uid, collection, transaction_id)
        if record:
            record["type"] = kind
            return collection, record
    return None


def create_transaction(uid: str, kind: str, data: dict[str, Any]) -> str:
    return create_record(uid, COLLECTION_FOR_KIND[kind], data)


def update_transaction(uid: str, transaction_id: str, kind: str, data: dict[str, Any]) -> None:
    existing = get_transaction(uid, transaction_id)
    target_collection = COLLECTION_FOR_KIND[kind]
    if existing and existing[0] != target_collection:
        delete_record(uid, existing[0], transaction_id)
        create_record(uid, target_collection, data)
    else:
        set_record(uid, target_collection, transaction_id, data)


def delete_transaction(uid: str, transaction_id: str) -> None:
    existing = get_transaction(uid, transaction_id)
    if existing:
        delete_record(uid, existing[0], transaction_id)


def list_goals(uid: str) -> list[dict[str, Any]]:
    return sorted(list_collection(uid, GOALS), key=lambda row: str(row.get("target_date") or "9999"))


def list_investments(uid: str) -> list[dict[str, Any]]:
    return sorted(list_collection(uid, INVESTMENTS), key=lambda row: str(row.get("createdAt", "")), reverse=True)


def list_debts(uid: str) -> list[dict[str, Any]]:
    return sorted(list_collection(uid, LEND_BORROW), key=lambda row: (row.get("status", ""), str(row.get("due_date") or "")))


def list_recurring(uid: str) -> list[dict[str, Any]]:
    return sorted(list_collection(uid, RECURRING), key=lambda row: str(row.get("next_due") or "9999"))


def list_wishlist(uid: str) -> list[dict[str, Any]]:
    return sorted(list_collection(uid, WISHLIST), key=lambda row: str(row.get("createdAt", "")), reverse=True)


def log_report(uid: str, report_type: str) -> None:
    create_record(uid, REPORTS, {"type": report_type})


def list_custom_budgets(uid: str) -> list[dict[str, Any]]:
    from app.firebase.schema import CUSTOM_BUDGETS
    return list_collection(uid, CUSTOM_BUDGETS)
