# Xray Manual Provisioning

This guide describes the first safe manual provisioning flow for real Xray/VLESS nodes.
It does not require SSH automation and does not install Xray on servers.

## Goal

The flow connects Baza users to manually configured Xray nodes:

```text
Baza User
  -> VpnCredential
  -> Xray inbound client UUID
  -> Subscription URL
  -> Happ
```

## Safety Rules

Never expose these values in CLI output, Telegram, subscription responses, screenshots, or logs:

- REALITY private key
- `SECRET_KEY`
- `BOT_TOKEN`
- database password
- subscription token

The CLI exports only client-side data needed to add a user manually to a node.

## Prerequisites

1. Apply database migrations:

```bash
alembic upgrade head
```

2. Configure the backend for Xray rendering when ready:

```bash
VPN_PROVIDER=xray
```

3. Create or update one `vpn_servers` row for each real node with public client config:

```text
name
country
host
port
protocol=vless
transport=tcp
security=reality
public_key
server_name
short_id
fingerprint=chrome
flow=xtls-rprx-vision
enabled=true
status=active
```

The REALITY private key stays only on the Xray node or in secure secret storage. It is
not stored in PostgreSQL by this MVP.

## Check Credential

Check whether Baza already has a credential for a user and node:

```bash
python -m app.cli vpn check-credential --user-id 123 --server-id 1
```

JSON mode:

```bash
python -m app.cli vpn check-credential --user-id 123 --server-id 1 --json
```

If no credential exists, this command does not create one.

## Export User For Manual Node Provisioning

Export safe provisioning data:

```bash
python -m app.cli vpn export-user --user-id 123 --server-id 1
```

JSON mode:

```bash
python -m app.cli vpn export-user --user-id 123 --server-id 1 --json
```

Repeated export is idempotent: Baza reuses the same `credential_id` for the same
`user_id + server_id` pair.

Example JSON shape with placeholders:

```json
{
  "credential_id": "11111111-1111-4111-8111-111111111111",
  "credential_status": "active",
  "fingerprint": "chrome",
  "flow": "xtls-rprx-vision",
  "host": "nl.example.com",
  "port": 443,
  "protocol": "vless",
  "public_key": "REALITY_PUBLIC_KEY",
  "security": "reality",
  "server_id": 1,
  "server_name": "NL",
  "server_name_sni": "www.microsoft.com",
  "short_id": "a1b2c3",
  "transport": "tcp",
  "user_id": 123
}
```

## Add Client To Xray Manually

On the target Xray node, add the exported `credential_id` as a VLESS client UUID to the
matching inbound.

Manual checklist:

1. Open the node's Xray inbound configuration.
2. Find the VLESS + REALITY inbound that matches the Baza `vpn_servers` row.
3. Add a client with:

```text
id: <credential_id from Baza>
flow: <flow from Baza>
```

4. Keep REALITY private key unchanged on the server.
5. Do not copy Baza subscription tokens into Xray config.
6. Reload/restart Xray using your normal operational process.

## Verify Xray Config

Check manually that the node config matches Baza:

```text
Baza host          == Xray public host
Baza port          == Xray inbound port
Baza security      == reality
Baza transport     == tcp
Baza public_key    == client-side REALITY public key
Baza server_name   == SNI/serverName expected by REALITY
Baza short_id      == allowed REALITY short ID
Baza credential_id == VLESS client UUID on the node
```

## Test With Happ

1. In Telegram, get the user's connection link.
2. Open the link in Happ or add it as a subscription URL.
3. Refresh subscription in Happ.
4. Confirm that the node appears.
5. Connect and test traffic.

The subscription endpoint returns working configs only when:

- the user is not blocked;
- the subscription is trial/active and not expired;
- the node is enabled and active;
- the credential is active;
- the node public config is valid.

## Three Node MVP

Repeat the export and manual Xray client addition for each node:

```bash
python -m app.cli vpn export-user --user-id 123 --server-id 1 --json
python -m app.cli vpn export-user --user-id 123 --server-id 2 --json
python -m app.cli vpn export-user --user-id 123 --server-id 3 --json
```

The Happ subscription will then include three `vless://` lines for the user.

## Future Automation

Later, the same `VpnCredential` data can be used by a provisioning adapter or reconcile
job. That future work should add sync status and node API integration behind
`VpnService`/`VpnProvider`, without changing Telegram UX.
