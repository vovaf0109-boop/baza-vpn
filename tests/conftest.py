import os

os.environ.setdefault("BOT_TOKEN", "")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SUPPORT_USERNAME", "baza_support")
os.environ.setdefault("SUBSCRIPTION_BASE_URL", "https://sub.example.com")
os.environ.setdefault("REDIS_URL", "")

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.device_service import DeviceService  # noqa: E402
from app.services.payment_service import PaymentService  # noqa: E402
from app.services.subscription_service import SubscriptionService  # noqa: E402
from app.services.user_service import UserService  # noqa: E402
from app.services.vpn_service import VpnService  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        bot_token="",
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        secret_key="test-secret-key",
        support_username="baza_support",
        subscription_base_url="https://sub.example.com",
        happ_download_url="https://www.happ.su/main",
        trial_days=7,
        device_limit=3,
        subscription_price_rub=299,
        subscription_days=30,
    )


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session
    await engine.dispose()


@pytest.fixture
def user_service(session: AsyncSession) -> UserService:
    return UserService(session)


@pytest.fixture
def subscription_service(session: AsyncSession, settings: Settings) -> SubscriptionService:
    return SubscriptionService(session, settings)


@pytest.fixture
def device_service(session: AsyncSession, settings: Settings) -> DeviceService:
    return DeviceService(session, settings)


@pytest.fixture
def payment_service(
    session: AsyncSession,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> PaymentService:
    return PaymentService(session, subscription_service, settings)


@pytest.fixture
def vpn_service(
    session: AsyncSession,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> VpnService:
    return VpnService(session, subscription_service, settings)
