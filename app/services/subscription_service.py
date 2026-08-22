import logging
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.enums import SubscriptionStatus
from app.exceptions import TrialAlreadyUsedError, UserBlockedError
from app.models import Subscription, User
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.utils.datetime import ensure_utc, utcnow
from app.utils.security import generate_subscription_token

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self._repo = SubscriptionRepository(session)

    async def get_by_user_id(self, user_id: int) -> Subscription | None:
        subscription = await self._repo.get_by_user_id(user_id)
        if subscription is None:
            return None
        return await self.refresh_status(subscription)

    async def get_by_token(self, token: str) -> Subscription | None:
        subscription = await self._repo.get_by_token(token)
        if subscription is None:
            return None
        return await self.refresh_status(subscription)

    async def get_current(self, user: User) -> Subscription | None:
        return await self.get_by_user_id(user.id)

    async def is_active(self, user: User) -> bool:
        subscription = await self.get_current(user)
        return subscription is not None and subscription.is_usable()

    async def refresh_status(self, subscription: Subscription) -> Subscription:
        if (
            subscription.status in {SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE}
            and ensure_utc(subscription.expires_at) <= utcnow()
        ):
            subscription.status = SubscriptionStatus.EXPIRED
            await self.session.flush()
            logger.info(
                "subscription_expired user_id=%s subscription_id=%s",
                subscription.user_id,
                subscription.id,
            )
        return subscription

    async def create_trial(self, user: User) -> Subscription:
        if user.is_blocked:
            raise UserBlockedError("blocked users cannot receive trial")

        await UserRepository(self.session).lock_by_id(user.id)
        existing = await self._repo.get_by_user_id(user.id, for_update=True)
        if existing is not None:
            raise TrialAlreadyUsedError("trial already exists for user")

        now = utcnow()
        subscription = Subscription(
            user_id=user.id,
            token=generate_subscription_token(),
            status=SubscriptionStatus.TRIAL,
            started_at=now,
            expires_at=now + timedelta(days=self.settings.trial_days),
            trial_used=True,
        )
        try:
            async with self.session.begin_nested():
                subscription = await self._repo.add(subscription)
        except IntegrityError as exc:
            existing = await self._repo.get_by_user_id(user.id, for_update=True)
            if existing is not None:
                raise TrialAlreadyUsedError("trial already exists for user") from exc
            raise

        logger.info(
            "trial_created user_id=%s subscription_id=%s days=%s",
            user.id,
            subscription.id,
            self.settings.trial_days,
        )
        return subscription

    async def get_or_create_token(self, user: User) -> str:
        subscription = await self.get_current(user)
        if subscription is None:
            raise TrialAlreadyUsedError("subscription is missing")
        if not subscription.token:
            subscription.token = generate_subscription_token()
            await self.session.flush()
        return subscription.token

    async def activate(self, user: User, *, days: int | None = None) -> Subscription:
        if user.is_blocked:
            raise UserBlockedError("blocked users cannot activate subscription")

        days = days or self.settings.subscription_days
        await UserRepository(self.session).lock_by_id(user.id)
        subscription = await self._repo.get_by_user_id(user.id, for_update=True)
        now = utcnow()

        if subscription is None:
            subscription = Subscription(
                user_id=user.id,
                token=generate_subscription_token(),
                status=SubscriptionStatus.ACTIVE,
                started_at=now,
                expires_at=now + timedelta(days=days),
                trial_used=False,
            )
            subscription = await self._repo.add(subscription)
        else:
            subscription = await self.refresh_status(subscription)
            if subscription.is_usable():
                subscription.expires_at = ensure_utc(subscription.expires_at) + timedelta(days=days)
            else:
                subscription.started_at = now
                subscription.expires_at = now + timedelta(days=days)
            subscription.status = SubscriptionStatus.ACTIVE

        await self.session.flush()
        logger.info(
            "subscription_activated user_id=%s subscription_id=%s days=%s",
            user.id,
            subscription.id,
            days,
        )
        return subscription

    async def extend(self, user: User, *, days: int | None = None) -> Subscription:
        return await self.activate(user, days=days)

    async def cancel(self, user: User) -> Subscription | None:
        subscription = await self._repo.get_by_user_id(user.id)
        if subscription is None:
            return None
        subscription.status = SubscriptionStatus.CANCELLED
        await self.session.flush()
        logger.info("subscription_cancelled user_id=%s", user.id)
        return subscription
