"""Application configuration.

Every sensitive value is read from environment variables. No secrets are
hard-coded, and safe development defaults are used only when a value is
missing. See ``.env.example`` for the full list.
"""
import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# Instance folder lives outside version control and holds the local SQLite file.
INSTANCE_DIR = BASE_DIR / "instance"


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    """Base configuration shared by every environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-change-me")
    SECRET_KEY_IS_DEFAULT = "SECRET_KEY" not in os.environ

    INSTANCE = str(INSTANCE_DIR)
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    _db_url = os.environ.get("DATABASE_URL")
    if _db_url:
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(INSTANCE_DIR / "veltrix.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Session / cookie hardening -------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), False)

    # --- CSRF ------------------------------------------------------------
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # token valid for the session lifetime

    # --- Business rules --------------------------------------------------
    DEMO_STARTING_BALANCE = Decimal(os.environ.get("DEMO_STARTING_BALANCE", "10000.00"))
    DEMO_CURRENCY = "USD"

    # Narrow CORS only for the configured frontend origins (JSON API only).
    CORS_ORIGINS = _split(os.environ.get("CORS_ORIGINS"))

    # Development bootstrap admin (only used by the seed command).
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip()
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    ADMIN_NAME = os.environ.get("ADMIN_NAME", "Veltrix Admin")

    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = True  # exercised on purpose by the test-suite
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "testing-secret-key"
    SECRET_KEY_IS_DEFAULT = False
    # Deterministic seed instrument set for assertions.
    DEMO_STARTING_BALANCE = Decimal("10000.00")


class ProductionConfig(Config):
    DEBUG = False


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> type[Config]:
    name = (name or os.environ.get("FLASK_ENV") or "development").lower()
    return CONFIGS.get(name, DevelopmentConfig)
