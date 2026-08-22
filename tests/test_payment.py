import pytest

from app.enums import PaymentStatus, SubscriptionStatus
from app.exceptions import UserBlockedError
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_payment_idempotency(
    user_service: UserService,
    subscription_service: SubscriptionService,
    payment_service: PaymentService,
) -> None:
    user = await user_service.create(telegram_id=4001, username="pay", first_name="Pay")
    trial = await subscription_service.create_trial(user)
    original_expires = trial.expires_at

    first, applied_first = await payment_service.complete_payment(
        provider="stub",
        provider_payment_id="tx-same-1",
        user=user,
        days=30,
    )
    assert applied_first is True
    assert first.status == PaymentStatus.PAID

    current = await subscription_service.get_current(user)
    assert current is not None
    assert current.status == SubscriptionStatus.ACTIVE
    first_expires = current.expires_at

    second, applied_second = await payment_service.complete_payment(
        provider="stub",
        provider_payment_id="tx-same-1",
        user=user,
        days=30,
    )
    assert applied_second is False
    assert second.id == first.id

    after = await subscription_service.get_current(user)
    assert after is not None
    assert after.expires_at == first_expires
    assert after.expires_at != original_expires


@pytest.mark.asyncio
async def test_start_checkout_reuses_pending_payment(
    user_service: UserService,
    payment_service: PaymentService,
) -> None:
    user = await user_service.create(telegram_id=4002, username="buy", first_name="Buy")

    first, _ = await payment_service.start_checkout(user)
    second, _ = await payment_service.start_checkout(user)

    assert first.id == second.id
    assert first.status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_blocked_user_cannot_start_checkout(
    user_service: UserService,
    payment_service: PaymentService,
) -> None:
    user = await user_service.create(telegram_id=4003, username="blocked", first_name="Blocked")
    await user_service.block(user)

    with pytest.raises(UserBlockedError):
        await payment_service.start_checkout(user)
