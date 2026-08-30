from __future__ import annotations

from dataclasses import dataclass
import json
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import VpnCredentialStatus
from app.models import User, VpnCredential, VpnServer
from app.repositories.vpn_credential_repository import VpnCredentialRepository
from app.services.vpn_providers import VlessConfig, VlessConfigFormatter, VpnProviderConfigurationError


class CliError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProvisioningData:
    user_id: int
    server_id: int
    server_name: str
    host: str
    port: int
    credential_id: str
    credential_status: str
    protocol: str
    encryption: str
    transport: str
    security: str
    public_key: str
    server_name_sni: str
    short_id: str | None
    fingerprint: str
    flow: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "host": self.host,
            "port": self.port,
            "credential_id": self.credential_id,
            "credential_status": self.credential_status,
            "protocol": self.protocol,
            "encryption": self.encryption,
            "transport": self.transport,
            "security": self.security,
            "public_key": self.public_key,
            "server_name_sni": self.server_name_sni,
            "short_id": self.short_id,
            "fingerprint": self.fingerprint,
            "flow": self.flow,
        }


async def export_user_provisioning(
    session: AsyncSession,
    *,
    user_id: int,
    server_id: int,
) -> ProvisioningData:
    user = await session.get(User, user_id)
    if user is None:
        raise CliError("User not found")

    server = await session.get(VpnServer, server_id)
    if server is None:
        raise CliError("VPN server not found")

    _validate_server_public_config(server)
    credential = await _get_or_create_credential(session, user, server)
    data = _build_provisioning_data(user, server, credential)
    _validate_client_config(data)
    return data


async def check_credential(
    session: AsyncSession,
    *,
    user_id: int,
    server_id: int,
) -> dict[str, object]:
    repo = VpnCredentialRepository(session)
    credential = await repo.get_latest_by_user_server(user_id, server_id)
    if credential is None:
        return {
            "exists": False,
            "user_id": user_id,
            "server_id": server_id,
        }
    return {
        "exists": True,
        "user_id": user_id,
        "server_id": server_id,
        "credential_id": credential.credential_id,
        "credential_status": credential.status.value,
    }


def render_output(data: ProvisioningData | dict[str, object], *, as_json: bool) -> str:
    payload = data.as_dict() if isinstance(data, ProvisioningData) else data
    if as_json:
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return "\n".join(f"{key}: {value}" for key, value in payload.items()) + "\n"


async def _get_or_create_credential(
    session: AsyncSession,
    user: User,
    server: VpnServer,
) -> VpnCredential:
    repo = VpnCredentialRepository(session)
    credential = await repo.get_latest_by_user_server(user.id, server.id)
    if credential is not None:
        return credential
    return await repo.add(
        VpnCredential(
            user_id=user.id,
            server_id=server.id,
            credential_id=str(uuid4()),
            status=VpnCredentialStatus.ACTIVE,
        )
    )


def _build_provisioning_data(
    user: User,
    server: VpnServer,
    credential: VpnCredential,
) -> ProvisioningData:
    _validate_server_public_config(server)
    assert server.port is not None
    assert server.public_key is not None
    assert server.server_name is not None

    return ProvisioningData(
        user_id=user.id,
        server_id=server.id,
        server_name=server.name,
        host=server.host,
        port=server.port,
        credential_id=credential.credential_id,
        credential_status=credential.status.value,
        protocol=server.protocol,
        encryption="none",
        transport=server.transport,
        security=server.security,
        public_key=server.public_key,
        server_name_sni=server.server_name,
        short_id=server.short_id,
        fingerprint=server.fingerprint,
        flow=server.flow,
    )


def _validate_server_public_config(server: VpnServer) -> None:
    if server.port is None:
        raise CliError("VPN server port is missing")
    if not server.public_key:
        raise CliError("VPN server public REALITY key is missing")
    if not server.server_name:
        raise CliError("VPN server SNI/server_name is missing")


def _validate_client_config(data: ProvisioningData) -> None:
    try:
        VlessConfigFormatter().format(
            VlessConfig(
                uuid=data.credential_id,
                host=data.host,
                port=data.port,
                name=data.server_name,
                encryption=data.encryption,
                transport=data.transport,
                security=data.security,
                server_name=data.server_name_sni,
                fingerprint=data.fingerprint,
                public_key=data.public_key,
                short_id=data.short_id,
                flow=data.flow,
            )
        )
    except VpnProviderConfigurationError as exc:
        raise CliError(str(exc)) from exc
