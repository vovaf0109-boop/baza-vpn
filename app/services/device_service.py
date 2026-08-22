import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.enums import DeviceStatus
from app.exceptions import DeviceLimitReachedError, DeviceNotFoundError, UserBlockedError
from app.models import Device, User
from app.repositories.device_repository import DeviceRepository
from app.repositories.user_repository import UserRepository
from app.utils.security import generate_device_identifier

logger = logging.getLogger(__name__)

DEFAULT_DEVICE_NAME = "Телефон"


class DeviceService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self._repo = DeviceRepository(session)

    @property
    def limit(self) -> int:
        return self.settings.device_limit

    async def list_active(self, user: User) -> list[Device]:
        return await self._repo.list_by_user(user.id, active_only=True)

    async def count_active(self, user: User) -> int:
        return await self._repo.count_active(user.id)

    async def add(self, user: User, name: str) -> Device:
        if user.is_blocked:
            raise UserBlockedError("blocked users cannot add devices")

        await UserRepository(self.session).lock_by_id(user.id)
        current = await self.count_active(user)
        if current >= self.limit:
            raise DeviceLimitReachedError(current, self.limit)

        clean_name = name.strip()[:64] or DEFAULT_DEVICE_NAME
        device = Device(
            user_id=user.id,
            name=clean_name,
            identifier=generate_device_identifier(),
            status=DeviceStatus.ACTIVE,
            last_seen=datetime.now(UTC),
        )
        device = await self._repo.add(device)
        logger.info("device_added user_id=%s device_id=%s", user.id, device.id)
        return device

    async def get_or_create_default(self, user: User) -> Device:
        devices = await self.list_active(user)
        if devices:
            device = devices[0]
            device.last_seen = datetime.now(UTC)
            await self.session.flush()
            return device
        return await self.add(user, DEFAULT_DEVICE_NAME)

    async def revoke(self, user: User, device_id: int) -> Device:
        device = await self._repo.get_by_id(device_id)
        if device is None or device.user_id != user.id:
            raise DeviceNotFoundError("device not found")
        device.status = DeviceStatus.REVOKED
        await self.session.flush()
        logger.info("device_removed user_id=%s device_id=%s", user.id, device.id)
        return device
