from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings


class FirebaseNotConfigured(RuntimeError):
    """Raised when Firebase credentials are required but missing."""


def _service_account_dict() -> dict[str, Any] | None:
    if settings.firebase_credentials_json:
        try:
            data = json.loads(settings.firebase_credentials_json)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    if (
        settings.firebase_project_id
        and settings.firebase_client_email
        and settings.firebase_private_key
    ):
        return {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": settings.firebase_private_key.replace("\\n", "\n"),
            "client_email": settings.firebase_client_email,
            "client_id": os.getenv("FIREBASE_CLIENT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL", ""),
        }
    return None


def _local_service_account_path() -> Path | None:
    configured_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    candidates = [Path(configured_path)] if configured_path else []
    candidates.append(Path("serviceAccountKey.json"))
    candidates.append(Path("./serviceAccountKey.json"))
    for path in candidates:
        if path and path.exists() and path.is_file():
            return path
    return None


@lru_cache(maxsize=1)
def get_firebase_app() -> firebase_admin.App:
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    options: dict[str, Any] = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id

    # 1. Local service account JSON file (serviceAccountKey.json)
    local_key = _local_service_account_path()
    if local_key:
        credential = credentials.Certificate(str(local_key))
        return firebase_admin.initialize_app(credential, options)

    # 2. Environment variable JSON or split env variables
    account = _service_account_dict()
    if account:
        credential = credentials.Certificate(account)
        return firebase_admin.initialize_app(credential, options)

    # 3. Google Application Default Credentials
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return firebase_admin.initialize_app(credentials.ApplicationDefault(), options)

    raise FirebaseNotConfigured(
        "Firebase Admin credentials missing. Please place 'serviceAccountKey.json' in project root or set FIREBASE_CREDENTIALS_JSON in environment variables."
    )


def get_firestore_client() -> firestore.Client:
    return firestore.client(app=get_firebase_app())


def firebase_web_config() -> dict[str, str]:
    return {
        "apiKey": settings.firebase_web_api_key,
        "authDomain": settings.firebase_auth_domain,
        "projectId": settings.firebase_project_id,
        "storageBucket": settings.firebase_storage_bucket,
        "messagingSenderId": settings.firebase_messaging_sender_id,
        "appId": settings.firebase_app_id,
        "measurementId": settings.firebase_measurement_id,
    }


def is_web_configured() -> bool:
    config = firebase_web_config()
    return bool(config["apiKey"] and config["authDomain"] and config["projectId"])
