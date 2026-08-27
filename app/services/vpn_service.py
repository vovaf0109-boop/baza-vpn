import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.enums import VpnCredentialStatus
from app.exceptions import SubscriptionInactiveError, UserBlockedError
from app.models import User, VpnCredential, VpnServer
from app.repositories.user_repository import UserRepository
from app.repositories.vpn_credential_repository import VpnCredentialRepository
from app.repositories.vpn_server_repository import VpnServerRepository
from app.services.vpn_providers import VpnProvider, create_vpn_provider
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


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
        self.provider = provider or create_vpn_provider(self.settings)
        self._servers = VpnServerRepository(session)
        self._credentials = VpnCredentialRepository(session)

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
        credentials = await self._ensure_credentials(user, servers)
        if self.settings.vpn_provider == "xray" and servers and not credentials:
            return None
        logger.info("vpn_subscription_requested user_id=%s", user.id)
        payload = await self.provider.render_subscription(user, servers, credentials, self.settings)
        return payload or None

    async def get_connection_url(self, user: User) -> str:
        if user.is_blocked:
            raise UserBlockedError("user is blocked")
        if not await self.subscription_service.is_active(user):
            raise SubscriptionInactiveError("subscription is not active")

        token = await self.subscription_service.get_or_create_token(user)
        logger.info("vpn_subscription_requested user_id=%s", user.id)
        return self.settings.subscription_url(token)

    async def _ensure_credentials(
        self,
        user: User,
        servers: list[VpnServer],
    ) -> list[VpnCredential]:
        if not servers:
            return []

        await UserRepository(self.session).lock_by_id(user.id)
        credentials: list[VpnCredential] = []
        for server in servers:
            latest = await self._credentials.get_latest_by_user_server(user.id, server.id)
            if latest is None:
                latest = await self._credentials.add(
                    VpnCredential(
                        user_id=user.id,
                        server_id=server.id,
                        credential_id=str(uuid4()),
                        status=VpnCredentialStatus.ACTIVE,
                    )
                )
            if latest.status == VpnCredentialStatus.ACTIVE:
                credentials.append(latest)
        return credentials
