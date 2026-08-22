from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.config import Settings
from app.services.admin_service import AdminService
from app.services.device_service import DeviceService
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.vpn_service import VpnService


class DatabaseMiddleware(BaseMiddleware):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            user_service = UserService(session)
            subscription_service = SubscriptionService(session, self.settings)
            device_service = DeviceService(session, self.settings)
            payment_service = PaymentService(session, subscription_service, self.settings)
            vpn_service = VpnService(session, subscription_service, self.settings)
            admin_service = AdminService(
                session,
                user_service,
                subscription_service,
                device_service,
                payment_service,
                vpn_service,
            )
            data.update(
                {
                    "session": session,
                    "settings": self.settings,
                    "user_service": user_service,
                    "subscription_service": subscription_service,
                    "device_service": device_service,
                    "payment_service": payment_service,
                    "vpn_service": vpn_service,
                    "admin_service": admin_service,
                }
            )
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
