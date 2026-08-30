from urllib.parse import parse_qs, unquote, urlparse

import pytest

from app.services.vpn_providers import (
    VlessConfig,
    VlessConfigFormatter,
    VpnProviderConfigurationError,
)


def test_vless_formatter() -> None:
    url = VlessConfigFormatter().format(
        VlessConfig(
            uuid="11111111-1111-4111-8111-111111111111",
            host="nl.example.com",
            port=443,
            name="Baza VPN - NL",
            server_name="www.microsoft.com",
            public_key="public-key",
            short_id="a1b2c3",
        )
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "vless"
    assert parsed.username == "11111111-1111-4111-8111-111111111111"
    assert parsed.hostname == "nl.example.com"
    assert parsed.port == 443
    assert query["encryption"] == ["none"]
    assert query["type"] == ["tcp"]
    assert query["security"] == ["reality"]
    assert query["sni"] == ["www.microsoft.com"]
    assert query["fp"] == ["chrome"]
    assert query["pbk"] == ["public-key"]
    assert query["sid"] == ["a1b2c3"]
    assert query["flow"] == ["xtls-rprx-vision"]
    assert unquote(parsed.fragment) == "Baza VPN - NL"


def test_vless_formatter_omits_flow_when_disabled() -> None:
    url = VlessConfigFormatter().format(
        VlessConfig(
            uuid="11111111-1111-4111-8111-111111111111",
            host="de.example.com",
            port=443,
            name="Baza VPN - A 443 no-flow",
            server_name="www.microsoft.com",
            public_key="public-key",
            short_id="a1b2c3",
            flow=None,
        )
    )

    query = parse_qs(urlparse(url).query)

    assert "flow" not in query
    assert query["encryption"] == ["none"]
    assert query["type"] == ["tcp"]
    assert query["security"] == ["reality"]


def test_vless_url_encoding() -> None:
    url = VlessConfigFormatter().format(
        VlessConfig(
            uuid="22222222-2222-4222-8222-222222222222",
            host="de.example.com",
            port=8443,
            name="Baza VPN - Германия #1",
            server_name="cdn.example.com",
            public_key="abc+/=",
            short_id="deadbeef",
        )
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert "%20" in parsed.fragment
    assert unquote(parsed.fragment) == "Baza VPN - Германия #1"
    assert query["pbk"] == ["abc+/="]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("uuid", "not-a-uuid"),
        ("host", "bad host"),
        ("port", 0),
        ("encryption", "aes-128-gcm"),
        ("transport", "ws"),
        ("security", "tls"),
        ("server_name", None),
        ("public_key", None),
        ("short_id", "not-hex"),
    ],
)
def test_invalid_node_configuration(field: str, value: object) -> None:
    data = {
        "uuid": "33333333-3333-4333-8333-333333333333",
        "host": "fr.example.com",
        "port": 443,
        "name": "Baza VPN - FR",
        "encryption": "none",
        "transport": "tcp",
        "security": "reality",
        "server_name": "www.cloudflare.com",
        "public_key": "public-key",
        "short_id": "abc123",
    }
    data[field] = value

    with pytest.raises(VpnProviderConfigurationError):
        VlessConfigFormatter().format(VlessConfig(**data))
