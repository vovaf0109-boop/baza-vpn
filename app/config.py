from functools import lru_cache
import re

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.enums import VpnProviderName


VALID_APP_ENVS = {"development", "test", "production"}
SUPPORT_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"

    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://baza:change_me_local_only@localhost:5432/baza"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_recycle_seconds: int = 1800
    database_command_timeout_seconds: int = 30
    redis_url: str = ""
    secret_key: str = ""

    support_username: str = ""
    support_response_time: str = "обычно в течение нескольких часов"
    admin_telegram_ids: str = ""

    subscription_base_url: str = ""
    happ_download_url: str = "https://www.happ.su/main"
    allowed_hosts: str = "localhost,127.0.0.1"
    vpn_provider: str = VpnProviderName.MOCK.value

    app_name: str = "Baza VPN"
    trial_days: int = 7
    device_limit: int = 3
    subscription_price_rub: int = 299
    subscription_days: int = 30
    admin_max_extend_days: int = 366

    log_level: str = "INFO"

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        app_env = str(value or "development").strip().lower()
        if app_env not in VALID_APP_ENVS:
            raise ValueError("APP_ENV must be one of: development, test, production")
        return app_env

    @field_validator("support_username", mode="before")
    @classmethod
    def strip_at(cls, value: str) -> str:
        return str(value).lstrip("@").strip() if value else ""

    @field_validator("support_username")
    @classmethod
    def validate_support_username(cls, value: str) -> str:
        if value and not SUPPORT_USERNAME_RE.fullmatch(value):
            raise ValueError("SUPPORT_USERNAME must be a valid Telegram username without @")
        return value

    @field_validator("subscription_base_url", "happ_download_url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        if not value:
            return ""
        stripped = value.strip().rstrip("/")
        if not stripped.startswith(("https://", "http://")):
            raise ValueError("URL must start with http:// or https://")
        return stripped

    @field_validator("vpn_provider", mode="before")
    @classmethod
    def validate_vpn_provider(cls, value: str) -> str:
        provider = str(value or VpnProviderName.MOCK.value).strip().lower()
        if provider not in {item.value for item in VpnProviderName}:
            raise ValueError("VPN_PROVIDER must be one of: mock, xray")
        return provider

    @field_validator(
        "trial_days",
        "device_limit",
        "subscription_price_rub",
        "subscription_days",
        "admin_max_extend_days",
        "database_pool_size",
        "database_pool_recycle_seconds",
        "database_command_timeout_seconds",
    )
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("numeric settings must be positive")
        return value

    @field_validator("database_max_overflow")
    @classmethod
    def validate_non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("DATABASE_MAX_OVERFLOW must be non-negative")
        return value

    @model_validator(mode="after")
    def validate_runtime_safety(self) -> "Settings":
        self.admin_ids

        if self.app_env != "production":
            return self

        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required in production")
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        if not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg:// in production")
        db_url = make_url(self.database_url)
        if db_url.password in {None, "", "baza", "password", "change_me_local_only"}:
            raise ValueError("DATABASE_URL must contain a strong production database password")
        if not self.admin_ids:
            raise ValueError("ADMIN_TELEGRAM_IDS is required in production")
        if not self.subscription_base_url.startswith("https://"):
            raise ValueError("SUBSCRIPTION_BASE_URL must be https:// in production")
        if not self.happ_download_url.startswith("https://"):
            raise ValueError("HAPP_DOWNLOAD_URL must be https:// in production")
        if not self.allowed_hosts or "*" in self.allowed_hosts_list:
            raise ValueError("ALLOWED_HOSTS must be explicit in production")
        return self

    @property
    def admin_ids(self) -> frozenset[int]:
        if not self.admin_telegram_ids:
            return frozenset()
        ids: list[int] = []
        for part in self.admin_telegram_ids.split(","):
            part = part.strip()
            if part:
                admin_id = int(part)
                if admin_id <= 0:
                    raise ValueError("ADMIN_TELEGRAM_IDS must contain positive integers")
                ids.append(admin_id)
        return frozenset(ids)

    @property
    def allowed_hosts_list(self) -> tuple[str, ...]:
        hosts = tuple(part.strip() for part in self.allowed_hosts.split(",") if part.strip())
        return hosts or ("localhost", "127.0.0.1")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_enabled(self) -> bool:
        return not self.is_production

    @property
    def support_url(self) -> str | None:
        if not self.support_username:
            return None
        return f"https://t.me/{self.support_username}"

    def subscription_url(self, token: str) -> str:
        base = self.subscription_base_url.rstrip("/")
        if not base:
            return f"/s/{token}"
        return f"{base}/s/{token}"

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()
