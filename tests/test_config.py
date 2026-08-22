import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import create_app


def test_production_requires_critical_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            bot_token="",
            secret_key="short",
        database_url="postgresql+asyncpg://baza:strong-password@localhost:5432/baza",
            subscription_base_url="https://vpn.example.com",
            allowed_hosts="vpn.example.com",
        admin_telegram_ids="42",
        )


def test_production_accepts_explicit_safe_config() -> None:
    settings = Settings(
        app_env="production",
        bot_token="123456:token",
        secret_key="x" * 32,
        database_url="postgresql+asyncpg://baza:strong-password@localhost:5432/baza",
        subscription_base_url="https://vpn.example.com",
        allowed_hosts="vpn.example.com",
        admin_telegram_ids="42",
    )
    assert settings.is_production is True
    assert settings.docs_enabled is False
    assert settings.allowed_hosts_list == ("vpn.example.com",)


def test_invalid_support_username_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(support_username="../bad")


def test_production_rejects_development_database_password() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            bot_token="123456:token",
            secret_key="x" * 32,
            database_url="postgresql+asyncpg://baza:baza@localhost:5432/baza",
            subscription_base_url="https://vpn.example.com",
            allowed_hosts="vpn.example.com",
            admin_telegram_ids="42",
        )


def test_docs_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BOT_TOKEN", "123456:token")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://baza:strong-password@localhost:5432/baza")
    monkeypatch.setenv("SUBSCRIPTION_BASE_URL", "https://vpn.example.com")
    monkeypatch.setenv("ALLOWED_HOSTS", "vpn.example.com")
    monkeypatch.setenv("SUPPORT_USERNAME", "baza_support")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "42")
    get_settings.cache_clear()

    app = create_app()

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
    get_settings.cache_clear()
