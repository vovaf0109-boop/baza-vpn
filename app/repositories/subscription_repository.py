from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(
        self,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> Subscription | None:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token(
        self,
        token: str,
        *,
        for_update: bool = False,
    ) -> Subscription | None:
        stmt = select(Subscription).where(Subscription.token == token)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, subscription: Subscription) -> Subscription:
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription
