# VPN Provider

This document describes the backend abstraction used to prepare Baza VPN for real
Xray/VLESS nodes while keeping Telegram handlers independent from VPN protocol details.

## Architecture

```text
Telegram / Happ
  -> Baza Backend
  -> VpnService
  -> VpnProvider
  -> MockVpnProvider or XrayProvider
  -> VLESS subscription response
```

Telegram handlers only ask `VpnService` for a connection URL. The public Happ endpoint
`GET /s/{token}` asks `VpnService` for a subscription body. Handlers do not know about
Xray, VLESS, REALITY, server public keys, or client UUIDs.

## MockVpnProvider

`MockVpnProvider` is the default provider and remains available for local development
and tests:

```text
VPN_PROVIDER=mock
```

It never returns working VPN configs. It returns a plain text placeholder payload so the
existing bot and subscription-token flows continue to work without real nodes.

## XrayProvider

`XrayProvider` is enabled explicitly:

```text
VPN_PROVIDER=xray
```

It renders a standard text subscription for Happ:

```text
#profile-title: Baza VPN
#support-url: https://t.me/baza_support
vless://...
vless://...
vless://...
```

If enabled Xray nodes are absent or their public client configuration is incomplete,
the provider raises a configuration error. The API returns a safe response and does not
generate fake VLESS links.

## VpnServer

`VpnServer` represents a public VPN node configuration. For the Xray MVP it stores
client-side data needed to build VLESS links:

- `name`
- `country`
- `host`
- `port`
- `protocol`
- `transport`
- `security`
- `public_key`
- `server_name`
- `short_id`
- `fingerprint`
- `flow`
- `status`
- `enabled`
- `load`
- `created_at`
- `updated_at`

Only `enabled=True` and `status=active` servers are included in subscriptions.

## VpnCredential

`VpnCredential` links a Baza user to a specific VPN node:

- `user_id`
- `server_id`
- `credential_id`
- `status`
- `created_at`
- `revoked_at`

`credential_id` is a cryptographically random UUID used as the VLESS client ID. It is
not derived from Telegram ID, username, device identifier, or subscription token.

For the current MVP Baza creates one active credential per user per enabled node and
reuses it across repeated subscription requests. Revoked credentials are not recreated
automatically during subscription rendering.

## VLESS Configuration

VLESS URLs are built by `VlessConfigFormatter`, not by database repositories or Telegram
handlers.

The formatter supports the MVP parameters:

- UUID client ID
- host
- port
- `type=tcp`
- `security=reality`
- `sni`
- `fp`
- `pbk`
- `sid`
- `flow`

Query parameters and URL fragments are encoded with standard URL encoding.

## REALITY Key Handling

The subscription response includes the REALITY public key only:

```text
pbk=<public key>
```

The REALITY private key must never be stored in PostgreSQL as plain text, sent to
Telegram, included in subscription responses, or logged. Private node secrets belong in
server-side secret storage or node-local configuration outside this MVP backend.

`short_id` is validated as hexadecimal client-side configuration before a VLESS URL is
returned.

## Subscription Format

Happ receives a plain text subscription response:

```text
#profile-title: Baza VPN
#support-url: https://t.me/baza_support
vless://uuid@host:443?type=tcp&security=reality&sni=example.com&fp=chrome&pbk=public&sid=abc123&flow=xtls-rprx-vision#Baza%20VPN%20-%20NL
```

Denied users receive no working configs:

- malformed token: 404
- expired subscription: 404
- blocked user: 404
- revoked credentials only: 404
- provider misconfiguration: 503 with a safe generic message

## Three Nodes

Three real nodes are represented as three enabled `vpn_servers` rows. For each active
user, Baza creates or reuses one `vpn_credentials` row per node:

```text
user 1 + node NL -> UUID A
user 1 + node DE -> UUID B
user 1 + node FR -> UUID C
```

The resulting Happ subscription contains three `vless://` lines.

## Future Provisioning

Automatic node provisioning is intentionally out of scope for this MVP. Future work can
add:

- Xray API or panel integration;
- SSH-free reconcile jobs;
- credential sync status;
- credential rotation;
- node health and load sync;
- per-device credential binding.

These additions should stay behind `VpnService` and `VpnProvider` so Telegram UX and
subscription URLs remain stable.
