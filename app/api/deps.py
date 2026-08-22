from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.services.subscription_service import SubscriptionService
from app.services.vpn_service import VpnService


async def settings_dep() -> Settings:
    return get_settings()


async def session_dep() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


def vpn_service_dep(
    session: AsyncSession = Depends(session_dep),
    settings: Settings = Depends(settings_dep),
) -> VpnService:
    subscription_service = SubscriptionService(session, settings)
    return VpnService(session, subscription_service, settings)
