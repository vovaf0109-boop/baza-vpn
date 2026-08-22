import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Subscription, User, VpnServer
from app.services.device_service import DeviceService
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.vpn_service import VpnService

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(
        self,
        session: AsyncSession,
        user_service: UserService,
        subscription_service: SubscriptionService,
        device_service: DeviceService,
        payment_service: PaymentService,
        vpn_service: VpnService,
    ) -> None:
        self.session = session
        self.users = user_service
        self.subscriptions = subscription_service
        self.devices = device_service
        self.payments = payment_service
        self.vpn = vpn_service

    async def find_user(self, raw: str) -> User | None:
        value = raw.strip().lstrip("#")
        if not value.isdigit():
            return None
        number = int(value)
        user = await self.users.get_by_id(number)
        if user is not None:
            return user
        return await self.users.get_by_telegram_id(number)

    async def user_overview(self, user: User) -> dict:
        subscription = await self.subscriptions.get_current(user)
        devices = await self.devices.list_active(user)
        payments = await self.payments.list_for_user(user)
        return {
            "user": user,
            "subscription": subscription,
            "devices": devices,
            "payments": payments,
        }

    async def block_user(self, user: User) -> User:
        return await self.users.block(user)

    async def unblock_user(self, user: User) -> User:
        return await self.users.unblock(user)

    async def extend_subscription(self, user: User, days: int) -> Subscription:
        return await self.subscriptions.extend(user, days=days)

    async def list_payments(self, user: User) -> list[Payment]:
        return await self.payments.list_for_user(user)

    async def list_servers(self) -> list[VpnServer]:
        return await self.vpn.get_all_servers()
