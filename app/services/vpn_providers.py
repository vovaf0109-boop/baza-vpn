from dataclasses import dataclass
import re
from typing import Protocol
from urllib.parse import quote, urlencode
from uuid import UUID

from app.config import Settings
from app.enums import VpnCredentialStatus
from app.models import User, VpnCredential, VpnServer

HEX_RE = re.compile(r"^[0-9a-fA-F]*$")


class VpnProviderConfigurationError(RuntimeError):
    """Raised when server-side VPN configuration is incomplete or unsafe."""


class VpnProvider(Protocol):
    async def render_subscription(
        self,
        user: User,
        servers: list[VpnServer],
        credentials: list[VpnCredential],
        settings: Settings,
    ) -> str:
        """Build a subscription payload for a VPN client."""


@dataclass(frozen=True)
class VlessConfig:
    uuid: str
    host: str
    port: int
    name: str
    encryption: str = "none"
    transport: str = "tcp"
    security: str = "reality"
    server_name: str | None = None
    fingerprint: str = "chrome"
    public_key: str | None = None
    short_id: str | None = None
    flow: str | None = "xtls-rprx-vision"


class VlessConfigFormatter:
    def format(self, config: VlessConfig) -> str:
        self._validate(config)
        query: dict[str, str] = {
            "encryption": config.encryption,
            "type": config.transport,
            "security": config.security,
            "fp": config.fingerprint,
        }
        if config.server_name:
            query["sni"] = config.server_name
        if config.public_key:
            query["pbk"] = config.public_key
        if config.short_id:
            query["sid"] = config.short_id
        if config.flow:
            query["flow"] = config.flow

        encoded_query = urlencode(query)
        fragment = quote(config.name, safe="")
        return f"vless://{config.uuid}@{config.host}:{config.port}?{encoded_query}#{fragment}"

    def _validate(self, config: VlessConfig) -> None:
        try:
            UUID(config.uuid)
        except ValueError as exc:
            raise VpnProviderConfigurationError("invalid VLESS client UUID") from exc

        if not config.host or any(char in config.host for char in (" ", "/", "?", "#", "@")):
            raise VpnProviderConfigurationError("invalid VPN server host")
        if config.port <= 0 or config.port > 65535:
            raise VpnProviderConfigurationError("invalid VPN server port")
        if config.encryption != "none":
            raise VpnProviderConfigurationError("unsupported VLESS encryption")
        if config.transport != "tcp":
            raise VpnProviderConfigurationError("unsupported VLESS transport")
        if config.security != "reality":
            raise VpnProviderConfigurationError("unsupported VLESS security")
        if not config.server_name:
            raise VpnProviderConfigurationError("REALITY server_name is required")
        if not config.public_key:
            raise VpnProviderConfigurationError("REALITY public key is required")
        if config.short_id and (len(config.short_id) > 16 or not HEX_RE.fullmatch(config.short_id)):
            raise VpnProviderConfigurationError("REALITY short_id must be hex")


class MockVpnProvider:
    """Test provider that deliberately does not expose real VPN configs."""

    async def render_subscription(
        self,
        user: User,
        servers: list[VpnServer],
        credentials: list[VpnCredential],
        settings: Settings,
    ) -> str:
        lines = [
            "# Baza VPN",
            "# Подписка активна. Реальные серверы появятся после подключения VPN-провайдера.",
        ]
        if servers:
            lines.append(f"# Доступно локаций: {len(servers)}")
        return "\n".join(lines) + "\n"


class XrayProvider:
    def __init__(self, formatter: VlessConfigFormatter | None = None) -> None:
        self.formatter = formatter or VlessConfigFormatter()

    async def get_available_servers(self, servers: list[VpnServer]) -> list[VpnServer]:
        return servers

    async def get_user_credentials(
        self,
        credentials: list[VpnCredential],
    ) -> list[VpnCredential]:
        return [
            credential
            for credential in credentials
            if credential.status == VpnCredentialStatus.ACTIVE
        ]

    async def get_subscription_configs(
        self,
        servers: list[VpnServer],
        credentials: list[VpnCredential],
    ) -> list[str]:
        if not servers:
            raise VpnProviderConfigurationError("no enabled Xray servers configured")

        credential_by_server_id = {
            credential.server_id: credential
            for credential in await self.get_user_credentials(credentials)
        }
        configs: list[str] = []
        for server in await self.get_available_servers(servers):
            credential = credential_by_server_id.get(server.id)
            if credential is None:
                continue
            configs.append(self.formatter.format(self._to_vless_config(server, credential)))
        return configs

    async def revoke_user(self, user: User) -> None:
        return None

    async def render_subscription(
        self,
        user: User,
        servers: list[VpnServer],
        credentials: list[VpnCredential],
        settings: Settings,
    ) -> str:
        configs = await self.get_subscription_configs(servers, credentials)
        if not configs:
            return ""

        lines = [f"#profile-title: {settings.app_name}"]
        if settings.support_url:
            lines.append(f"#support-url: {settings.support_url}")
        lines.extend(configs)
        return "\n".join(lines) + "\n"

    def _to_vless_config(self, server: VpnServer, credential: VpnCredential) -> VlessConfig:
        if server.port is None:
            raise VpnProviderConfigurationError("VPN server port is required")
        return VlessConfig(
            uuid=credential.credential_id,
            host=server.host,
            port=server.port,
            name=f"Baza VPN - {server.name}",
            transport=server.transport,
            security=server.security,
            server_name=server.server_name,
            fingerprint=server.fingerprint,
            public_key=server.public_key,
            short_id=server.short_id,
            flow=server.flow,
        )


def create_vpn_provider(settings: Settings) -> VpnProvider:
    if settings.vpn_provider == "xray":
        return XrayProvider()
    return MockVpnProvider()
