from datetime import timedelta

import pytest

from app.enums import SubscriptionStatus
from app.exceptions import TrialAlreadyUsedError, UserBlockedError
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.utils.datetime import utcnow
from app.utils.security import generate_subscription_token


@pytest.mark.asyncio
async def test_trial_creation(
    user_service: UserService,
    subscription_service: SubscriptionService,
) -> None:
    user = await user_service.create(telegram_id=2001, username="trial", first_name="Trial")
    subscription = await subscription_service.create_trial(user)
    assert subscription.status == SubscriptionStatus.TRIAL
    assert subscription.token
    assert subscription.is_usable()
    remaining = subscription.expires_at - subscription.started_at
    assert remaining >= timedelta(days=6, hours=23)


@pytest.mark.asyncio
async def test_trial_cannot_be_created_twice(
    user_service: UserService,
    subscription_service: SubscriptionService,
) -> None:
    user = await user_service.create(telegram_id=2002, username="twice", first_name="Twice")
    await subscription_service.create_trial(user)
    with pytest.raises(TrialAlreadyUsedError):
        await subscription_service.create_trial(user)


@pytest.mark.asyncio
async def test_subscription_expiration(
    user_service: UserService,
    subscription_service: SubscriptionService,
) -> None:
    user = await user_service.create(telegram_id=2003, username="exp", first_name="Exp")
    subscription = await subscription_service.create_trial(user)
    subscription.expires_at = utcnow() - timedelta(minutes=1)
    refreshed = await subscription_service.refresh_status(subscription)
    assert refreshed.status == SubscriptionStatus.EXPIRED
    assert not refreshed.is_usable()


@pytest.mark.asyncio
async def test_subscription_renewal(
    user_service: UserService,
    subscription_service: SubscriptionService,
) -> None:
    user = await user_service.create(telegram_id=2004, username="renew", first_name="Renew")
    subscription = await subscription_service.create_trial(user)
    subscription.expires_at = utcnow() - timedelta(days=1)
    await subscription_service.refresh_status(subscription)

    renewed = await subscription_service.extend(user, days=30)
    assert renewed.status == SubscriptionStatus.ACTIVE
    assert renewed.is_usable()
    assert renewed.token == subscription.token


@pytest.mark.asyncio
async def test_token_generation_is_unique() -> None:
    tokens = {generate_subscription_token() for _ in range(20)}
    assert len(tokens) == 20
    for token in tokens:
        assert len(token) >= 32


@pytest.mark.asyncio
async def test_blocked_user_cannot_receive_trial(
    user_service: UserService,
    subscription_service: SubscriptionService,
) -> None:
    user = await user_service.create(telegram_id=2005, username="blocked", first_name="Blocked")
    await user_service.block(user)

    with pytest.raises(UserBlockedError):
        await subscription_service.create_trial(user)


@pytest.mark.asyncio
async def test_blocked_user_cannot_activate_subscription(
    user_service: UserService,
    subscription_service: SubscriptionService,
) -> None:
    user = await user_service.create(telegram_id=2006, username="blocked2", first_name="Blocked")
    await user_service.block(user)

    with pytest.raises(UserBlockedError):
        await subscription_service.activate(user, days=30)
