from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.enums import VpnCredentialStatus, VpnServerStatus
from app.exceptions import SubscriptionInactiveError
from app.models import VpnCredential, VpnServer
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.vpn_service import VpnService
from app.utils.datetime import utcnow


def xray_settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"vpn_provider": "xray", "support_username": "baza_support"})


async def add_xray_server(
    session: AsyncSession,
    *,
    name: str,
    host: str,
    load: int = 0,
    enabled: bool = True,
    status: VpnServerStatus = VpnServerStatus.ACTIVE,
    port: int | None = 443,
    public_key: str | None = "public-key",
    server_name: str | None = "www.microsoft.com",
    short_id: str | None = "a1b2c3",
) -> VpnServer:
    server = VpnServer(
        name=name,
        country=name,
        host=host,
        port=port,
        protocol="vless",
        transport="tcp",
        security="reality",
        public_key=public_key,
        server_name=server_name,
        short_id=short_id,
        fingerprint="chrome",
        flow="xtls-rprx-vision",
        load=load,
        enabled=enabled,
        status=status,
    )
    session.add(server)
    await session.flush()
    return server


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


@pytest.mark.asyncio
async def test_subscription_contains_three_configs(
    session: AsyncSession,
    user_service: UserService,
    settings: Settings,
) -> None:
    current_settings = xray_settings(settings)
    subscription_service = SubscriptionService(session, current_settings)
    vpn_service = VpnService(session, subscription_service, current_settings)
    user = await user_service.create(telegram_id=5101, username="xray", first_name="Xray")
    subscription = await subscription_service.create_trial(user)
    await add_xray_server(session, name="NL", host="nl.example.com", load=2)
    await add_xray_server(session, name="DE", host="de.example.com", load=1)
    await add_xray_server(session, name="FR", host="fr.example.com", load=3)

    payload = await vpn_service.get_subscription(subscription.token)

    assert payload is not None
    assert payload.startswith("#profile-title: Baza VPN")
    assert "#support-url: https://t.me/baza_support" in payload
    assert payload.count("vless://") == 3


@pytest.mark.asyncio
async def test_subscription_excludes_private_key(
    session: AsyncSession,
    user_service: UserService,
    settings: Settings,
) -> None:
    current_settings = xray_settings(settings)
    subscription_service = SubscriptionService(session, current_settings)
    vpn_service = VpnService(session, subscription_service, current_settings)
    user = await user_service.create(telegram_id=5102, username="safe", first_name="Safe")
    subscription = await subscription_service.create_trial(user)
    await add_xray_server(session, name="NL", host="nl.example.com")

    payload = await vpn_service.get_subscription(subscription.token)

    assert payload is not None
    for forbidden in {
        "private_key",
        "secret_key",
        "database password",
        "BOT_TOKEN",
        current_settings.secret_key,
    }:
        assert forbidden not in payload


@pytest.mark.asyncio
async def test_expired_subscription_no_configs(
    session: AsyncSession,
    user_service: UserService,
    settings: Settings,
) -> None:
    current_settings = xray_settings(settings)
    subscription_service = SubscriptionService(session, current_settings)
    vpn_service = VpnService(session, subscription_service, current_settings)
    user = await user_service.create(telegram_id=5103, username="expired", first_name="Expired")
    subscription = await subscription_service.create_trial(user)
    subscription.expires_at = utcnow() - timedelta(hours=1)
    await subscription_service.refresh_status(subscription)
    await add_xray_server(session, name="NL", host="nl.example.com")

    payload = await vpn_service.get_subscription(subscription.token)

    assert payload is None


@pytest.mark.asyncio
async def test_blocked_user_no_configs(
    session: AsyncSession,
    user_service: UserService,
    settings: Settings,
) -> None:
    current_settings = xray_settings(settings)
    subscription_service = SubscriptionService(session, current_settings)
    vpn_service = VpnService(session, subscription_service, current_settings)
    user = await user_service.create(telegram_id=5104, username="blocked", first_name="Blocked")
    subscription = await subscription_service.create_trial(user)
    await user_service.block(user)
    await add_xray_server(session, name="NL", host="nl.example.com")

    payload = await vpn_service.get_subscription(subscription.token)

    assert payload is None


@pytest.mark.asyncio
async def test_revoked_credential_no_configs(
    session: AsyncSession,
    user_service: UserService,
    settings: Settings,
) -> None:
    current_settings = xray_settings(settings)
    subscription_service = SubscriptionService(session, current_settings)
    vpn_service = VpnService(session, subscription_service, current_settings)
    user = await user_service.create(telegram_id=5105, username="revoked", first_name="Revoked")
    subscription = await subscription_service.create_trial(user)
    await add_xray_server(session, name="NL", host="nl.example.com")
    first_payload = await vpn_service.get_subscription(subscription.token)
    assert first_payload is not None

    credential = (await session.execute(select(VpnCredential))).scalar_one()
    credential.status = VpnCredentialStatus.REVOKED
    credential.revoked_at = datetime.now(UTC)
    await session.flush()

    payload = await vpn_service.get_subscription(subscription.token)

    assert payload is None


@pytest.mark.asyncio
async def test_subscription_token_idempotency(
    session: AsyncSession,
    user_service: UserService,
    settings: Settings,
) -> None:
    current_settings = xray_settings(settings)
    subscription_service = SubscriptionService(session, current_settings)
    vpn_service = VpnService(session, subscription_service, current_settings)
    user = await user_service.create(telegram_id=5106, username="stable", first_name="Stable")
    subscription = await subscription_service.create_trial(user)
    await add_xray_server(session, name="NL", host="nl.example.com")
    await add_xray_server(session, name="DE", host="de.example.com")

    first_payload = await vpn_service.get_subscription(subscription.token)
    first_credentials = list(
        (await session.execute(select(VpnCredential.credential_id))).scalars().all()
    )
    second_payload = await vpn_service.get_subscription(subscription.token)
    second_credentials = list(
        (await session.execute(select(VpnCredential.credential_id))).scalars().all()
    )

    assert first_payload == second_payload
    assert first_credentials == second_credentials
    assert len(second_credentials) == 2


@pytest.mark.asyncio
async def test_multiple_nodes(
    session: AsyncSession,
    user_service: UserService,
    settings: Settings,
) -> None:
    current_settings = xray_settings(settings)
    subscription_service = SubscriptionService(session, current_settings)
    vpn_service = VpnService(session, subscription_service, current_settings)
    user = await user_service.create(telegram_id=5107, username="nodes", first_name="Nodes")
    subscription = await subscription_service.create_trial(user)
    await add_xray_server(session, name="DE", host="de.example.com", load=2)
    await add_xray_server(session, name="NL", host="nl.example.com", load=1)
    await add_xray_server(
        session,
        name="Disabled",
        host="disabled.example.com",
        enabled=False,
    )
    await add_xray_server(
        session,
        name="Maintenance",
        host="maintenance.example.com",
        status=VpnServerStatus.MAINTENANCE,
    )

    payload = await vpn_service.get_subscription(subscription.token)

    assert payload is not None
    assert payload.count("vless://") == 2
    assert payload.index("nl.example.com") < payload.index("de.example.com")
    assert "disabled.example.com" not in payload
    assert "maintenance.example.com" not in payload
