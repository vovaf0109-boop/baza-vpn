import logging
import secrets
from typing import Protocol

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.enums import PaymentProviderName, PaymentStatus
from app.exceptions import PaymentAlreadyProcessedError, PaymentNotFoundError, UserBlockedError
from app.models import Payment, User
from app.repositories.payment_repository import PaymentRepository
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class PaymentProvider(Protocol):
    name: str

    async def create_checkout(self, user: User, payment: Payment) -> str | None:
        """Вернуть URL оплаты или None, если оплата ещё не подключена."""


class StubPaymentProvider:
    name = PaymentProviderName.STUB

    async def create_checkout(self, user: User, payment: Payment) -> str | None:
        return None


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        subscription_service: SubscriptionService,
        settings: Settings | None = None,
        provider: PaymentProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.subscription_service = subscription_service
        self.provider = provider or StubPaymentProvider()
        self._repo = PaymentRepository(session)

    async def list_for_user(self, user: User, *, limit: int = 20) -> list[Payment]:
        return await self._repo.list_by_user(user.id, limit=limit)

    async def get_by_id(self, payment_id: int) -> Payment | None:
        return await self._repo.get_by_id(payment_id)

    async def create_payment(
        self,
        user: User,
        *,
        provider: str | None = None,
        provider_payment_id: str | None = None,
        amount: int | None = None,
        currency: str = "RUB",
    ) -> Payment:
        if user.is_blocked:
            raise UserBlockedError("blocked users cannot create payments")

        payment = Payment(
            user_id=user.id,
            provider=provider or self.provider.name,
            provider_payment_id=provider_payment_id or f"pending_{secrets.token_hex(16)}",
            amount=amount if amount is not None else self.settings.subscription_price_rub,
            currency=currency,
            status=PaymentStatus.PENDING,
        )
        payment = await self._repo.add(payment)
        logger.info(
            "payment_created payment_id=%s user_id=%s provider=%s amount=%s",
            payment.id,
            user.id,
            payment.provider,
            payment.amount,
        )
        return payment

    async def start_checkout(self, user: User) -> tuple[Payment, str | None]:
        if user.is_blocked:
            raise UserBlockedError("blocked users cannot start checkout")

        pending = await self._repo.get_latest_pending_by_user(user.id, str(self.provider.name))
        if pending is not None:
            checkout_url = await self.provider.create_checkout(user, pending)
            return pending, checkout_url

        payment = await self.create_payment(user)
        checkout_url = await self.provider.create_checkout(user, payment)
        return payment, checkout_url

    async def complete_payment(
        self,
        *,
        provider: str,
        provider_payment_id: str,
        user: User | None = None,
        days: int | None = None,
    ) -> tuple[Payment, bool]:
        """
        Подтвердить платёж и активировать подписку.

        Возвращает (payment, applied). applied=False если платёж уже обработан.
        """
        payment = await self._repo.get_by_provider_id(
            provider,
            provider_payment_id,
            for_update=True,
        )
        if payment is None:
            if user is None:
                raise PaymentNotFoundError("payment not found")
            try:
                async with self.session.begin_nested():
                    payment = await self.create_payment(
                        user,
                        provider=provider,
                        provider_payment_id=provider_payment_id,
                    )
            except IntegrityError as exc:
                payment = await self._repo.get_by_provider_id(
                    provider,
                    provider_payment_id,
                    for_update=True,
                )
                if payment is None:
                    raise PaymentNotFoundError("payment not found") from exc

        if payment.status == PaymentStatus.PAID:
            logger.info(
                "payment_already_processed payment_id=%s provider=%s",
                payment.id,
                provider,
            )
            return payment, False

        if payment.status in {PaymentStatus.FAILED, PaymentStatus.REFUNDED}:
            raise PaymentAlreadyProcessedError("payment is not pending")

        owner = user or await user_from_payment(self.session, payment.user_id)
        payment.status = PaymentStatus.PAID
        await self.session.flush()
        await self.subscription_service.activate(owner, days=days)
        logger.info(
            "payment_completed payment_id=%s user_id=%s",
            payment.id,
            owner.id,
        )
        return payment, True


async def user_from_payment(session: AsyncSession, user_id: int) -> User:
    from app.services.user_service import UserService

    user = await UserService(session).get_by_id(user_id)
    if user is None:
        raise PaymentNotFoundError("payment user not found")
    return user
