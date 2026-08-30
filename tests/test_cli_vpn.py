import json
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.vpn import CliError, check_credential, export_user_provisioning, render_output
from app.models import User, VpnCredential, VpnServer


async def add_user(session: AsyncSession) -> User:
    user = User(telegram_id=9001, username="manual", first_name="Manual")
    session.add(user)
    await session.flush()
    return user


async def add_server(
    session: AsyncSession,
    *,
    public_key: str | None = "public-key",
) -> VpnServer:
    server = VpnServer(
        name="NL",
        country="NL",
        host="nl.example.com",
        port=443,
        protocol="vless",
        transport="tcp",
        security="reality",
        public_key=public_key,
        server_name="www.microsoft.com",
        short_id="a1b2c3",
        fingerprint="chrome",
        flow="xtls-rprx-vision",
    )
    session.add(server)
    await session.flush()
    return server


@pytest.mark.asyncio
async def test_export_user_provisioning_json_contains_only_safe_data(
    session: AsyncSession,
) -> None:
    user = await add_user(session)
    server = await add_server(session)

    data = await export_user_provisioning(session, user_id=user.id, server_id=server.id)
    rendered = render_output(data, as_json=True)
    payload = json.loads(rendered)

    UUID(payload["credential_id"])
    assert payload["user_id"] == user.id
    assert payload["server_id"] == server.id
    assert payload["server_name"] == "NL"
    assert payload["host"] == "nl.example.com"
    assert payload["port"] == 443
    assert payload["protocol"] == "vless"
    assert payload["encryption"] == "none"
    assert payload["transport"] == "tcp"
    assert payload["security"] == "reality"
    assert payload["public_key"] == "public-key"
    assert payload["server_name_sni"] == "www.microsoft.com"
    assert payload["short_id"] == "a1b2c3"
    assert payload["flow"] == "xtls-rprx-vision"
    for forbidden in {"private_key", "SECRET_KEY", "BOT_TOKEN", "DATABASE_PASSWORD", "token"}:
        assert forbidden not in rendered


@pytest.mark.asyncio
async def test_export_user_provisioning_is_idempotent(session: AsyncSession) -> None:
    user = await add_user(session)
    server = await add_server(session)

    first = await export_user_provisioning(session, user_id=user.id, server_id=server.id)
    second = await export_user_provisioning(session, user_id=user.id, server_id=server.id)
    total = await session.scalar(select(func.count()).select_from(VpnCredential))

    assert first.credential_id == second.credential_id
    assert total == 1


@pytest.mark.asyncio
async def test_check_credential_reports_missing_and_existing(session: AsyncSession) -> None:
    user = await add_user(session)
    server = await add_server(session)

    missing = await check_credential(session, user_id=user.id, server_id=server.id)
    await export_user_provisioning(session, user_id=user.id, server_id=server.id)
    existing = await check_credential(session, user_id=user.id, server_id=server.id)

    assert missing == {"exists": False, "user_id": user.id, "server_id": server.id}
    assert existing["exists"] is True
    assert existing["credential_status"] == "active"
    UUID(str(existing["credential_id"]))


@pytest.mark.asyncio
async def test_export_user_provisioning_rejects_invalid_node_without_creating_credential(
    session: AsyncSession,
) -> None:
    user = await add_user(session)
    server = await add_server(session, public_key=None)

    with pytest.raises(CliError):
        await export_user_provisioning(session, user_id=user.id, server_id=server.id)

    total = await session.scalar(select(func.count()).select_from(VpnCredential))
    assert total == 0


def test_render_output_text_mode() -> None:
    output = render_output(
        {
            "exists": True,
            "user_id": 1,
            "server_id": 2,
            "credential_id": "11111111-1111-4111-8111-111111111111",
        },
        as_json=False,
    )

    assert "exists: True" in output
    assert "credential_id: 11111111-1111-4111-8111-111111111111" in output
