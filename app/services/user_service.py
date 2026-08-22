import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import UserStatus
from app.models import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._repo = UserRepository(session)

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._repo.get_by_id(user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self._repo.get_by_telegram_id(telegram_id)

    async def create(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
    ) -> User:
        existing = await self._repo.get_by_telegram_id(telegram_id)
        if existing is not None:
            await self.update_profile(
                existing,
                username=username,
                first_name=first_name,
            )
            return existing

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            status=UserStatus.ACTIVE,
        )
        try:
            async with self.session.begin_nested():
                user = await self._repo.add(user)
        except IntegrityError:
            existing = await self._repo.get_by_telegram_id(telegram_id)
            if existing is None:
                raise
            return existing

        logger.info("user_created user_id=%s telegram_id=%s", user.id, user.telegram_id)
        return user

    async def update_profile(
        self,
        user: User,
        *,
        username: str | None,
        first_name: str | None,
    ) -> User:
        user.username = username
        user.first_name = first_name
        await self.session.flush()
        return user

    async def block(self, user: User) -> User:
        user.status = UserStatus.BLOCKED
        user.blocked_at = datetime.now(UTC)
        await self.session.flush()
        logger.info("user_blocked user_id=%s", user.id)
        return user

    async def unblock(self, user: User) -> User:
        user.status = UserStatus.ACTIVE
        user.blocked_at = None
        await self.session.flush()
        logger.info("user_unblocked user_id=%s", user.id)
        return user
