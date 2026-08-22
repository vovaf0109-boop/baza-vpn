import logging
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.exceptions import SubscriptionInactiveError, UserBlockedError
from app.models import User, VpnServer
from app.repositories.vpn_server_repository import VpnServerRepository
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class VpnProvider(Protocol):
    async def render_subscription(self, token: str, servers: list[VpnServer]) -> str:
        """Собрать payload для клиента. Реализацию можно заменить."""


class MockVpnProvider:
    """Заглушка: не привязана к протоколу. Позже заменить на реальный провайдер."""

    async def render_subscription(self, token: str, servers: list[VpnServer]) -> str:
        lines = [
            "# Baza VPN",
            "# Подписка активна. Реальные серверы появятся после подключения VPN-провайдера.",
        ]
        if servers:
            lines.append(f"# Доступно локаций: {len(servers)}")
        return "\n".join(lines) + "\n"


class VpnService:
    def __init__(
        self,
        session: AsyncSession,
        subscription_service: SubscriptionService,
        settings: Settings | None = None,
        provider: VpnProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.subscription_service = subscription_service
        self.provider = provider or MockVpnProvider()
        self._servers = VpnServerRepository(session)

    async def get_available_servers(self) -> list[VpnServer]:
        return await self._servers.list_available()

    async def get_all_servers(self) -> list[VpnServer]:
        return await self._servers.list_all()

    async def get_user_servers(self, user: User) -> list[VpnServer]:
        if not await self.is_subscription_active(user):
            return []
        return await self.get_available_servers()

    async def is_subscription_active(self, user: User) -> bool:
        if user.is_blocked:
            return False
        return await self.subscription_service.is_active(user)

    async def get_subscription(self, token: str) -> str | None:
        subscription = await self.subscription_service.get_by_token(token)
        if subscription is None or not subscription.is_usable():
            return None

        from app.services.user_service import UserService

        user = await UserService(self.session).get_by_id(subscription.user_id)
        if user is None or user.is_blocked:
            return None

        servers = await self.get_available_servers()
        logger.info("vpn_subscription_requested user_id=%s", user.id)
        return await self.provider.render_subscription(subscription.token, servers)

    async def get_connection_url(self, user: User) -> str:
        if user.is_blocked:
            raise UserBlockedError("user is blocked")
        if not await self.subscription_service.is_active(user):
            raise SubscriptionInactiveError("subscription is not active")

        token = await self.subscription_service.get_or_create_token(user)
        logger.info("vpn_subscription_requested user_id=%s", user.id)
        return self.settings.subscription_url(token)
