from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "D-OS")
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "http://127.0.0.1:8000")
    secret_key: str = os.getenv("SECRET_KEY", "")
    dev_bypass_login: str = os.getenv("DEV_BYPASS_LOGIN", "false")
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "dos_session")
    session_days: int = int(os.getenv("SESSION_DAYS", "7"))
    default_currency: str = os.getenv("DEFAULT_CURRENCY", "₹")

    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "")
    firebase_client_email: str = os.getenv("FIREBASE_CLIENT_EMAIL", "")
    firebase_private_key: str = os.getenv("FIREBASE_PRIVATE_KEY", "")
    firebase_credentials_json: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

    firebase_web_api_key: str = os.getenv("FIREBASE_API_KEY", "")
    firebase_auth_domain: str = os.getenv("FIREBASE_AUTH_DOMAIN", "")
    firebase_storage_bucket: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")
    firebase_messaging_sender_id: str = os.getenv("FIREBASE_MESSAGING_SENDER_ID", "")
    firebase_app_id: str = os.getenv("FIREBASE_APP_ID", "")
    firebase_measurement_id: str = os.getenv("FIREBASE_MEASUREMENT_ID", "")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def dev_bypass_enabled(self) -> bool:
        return self.app_env.lower() == "development" and self.dev_bypass_login.lower() == "true"


settings = Settings()

if settings.is_production and not settings.secret_key:
    import warnings
    warnings.warn(
        "SECRET_KEY is empty in production! Set a strong SECRET_KEY environment variable.",
        stacklevel=1,
    )
