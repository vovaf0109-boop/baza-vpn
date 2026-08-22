from datetime import timedelta

import pytest

from app.exceptions import SubscriptionInactiveError
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.vpn_service import VpnService
from app.utils.datetime import utcnow


@pytest.mark.asyncio
async def test_inactive_subscription_cannot_get_vpn_config(
    user_service: UserService,
    subscription_service: SubscriptionService,
    vpn_service: VpnService,
) -> None:
    user = await user_service.create(telegram_id=5001, username="vpn", first_name="Vpn")
    subscription = await subscription_service.create_trial(user)
    subscription.expires_at = utcnow() - timedelta(hours=1)
    await subscription_service.refresh_status(subscription)

    with pytest.raises(SubscriptionInactiveError):
        await vpn_service.get_connection_url(user)

    payload = await vpn_service.get_subscription(subscription.token)
    assert payload is None


@pytest.mark.asyncio
async def test_active_subscription_returns_stable_url(
    user_service: UserService,
    subscription_service: SubscriptionService,
    vpn_service: VpnService,
) -> None:
    user = await user_service.create(telegram_id=5002, username="ok", first_name="Ok")
    subscription = await subscription_service.create_trial(user)

    first = await vpn_service.get_connection_url(user)
    second = await vpn_service.get_connection_url(user)
    assert first == second
    assert subscription.token in first
    assert first.startswith("https://sub.example.com/s/")

    payload = await vpn_service.get_subscription(subscription.token)
    assert payload is not None
    assert "Baza VPN" in payload
