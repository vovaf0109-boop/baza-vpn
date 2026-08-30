# Xray Node Template

This is the canonical template for a Baza VPN Xray node after the lab matrix
on the Germany VPS. New nodes are copied from this template. They are not
configured with a unique mix of ports, flow, SNI, or transports.

## Lab vs production

The Germany node is the laboratory node. It may expose the A-D matrix so Happ
can compare one variable at a time. Production and every extra country node
must follow the canonical profile only.

```text
Telegram
  -> Baza backend
  -> HTTPS subscription
  -> Happ
  -> Germany Xray node
  -> Internet
```

## Canonical MVP profile

Until Happ confirms a different winner, new nodes use profile `A`:

```text
protocol:     vless
transport:    tcp
security:     reality
port:         443
flow:         unset (no xtls-rprx-vision)
encryption:   none
fingerprint:  chrome
```

Why this is the default:

- `443/tcp` is the least surprising public port for mobile networks.
- `flow` is a client compatibility risk in Happ/iOS. The lab keeps Vision as
  variants `B` and `D`; it is not the clone template.
- REALITY settings (`public_key`, `server_name`, `short_id`) stay the same
  across A-D. Only port or flow changes in the matrix.

## Controlled test matrix

Run only on the laboratory node. Do not buy a new VPS per variant.

| Code | Port | flow                 | What it tests      |
|------|------|----------------------|--------------------|
| A    | 443  | none                 | canonical baseline |
| B    | 443  | xtls-rprx-vision     | Vision on 443      |
| C    | 8443 | none                 | port 8443 baseline |
| D    | 8443 | xtls-rprx-vision     | original Vision    |

Xray constraint: one inbound per port. `flow` is per client, so A+B share the
`443` inbound and C+D share the `8443` inbound.

Baza constraint: each matrix cell is a separate `vpn_servers` row with its own
`VpnCredential` UUID. Happ then shows four named profiles.

## Inbound skeleton

Keep REALITY private key only on the node. Baza stores public client fields.

```json
{
  "inbounds": [
    {
      "tag": "vless-reality-443",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "<credential_id from Baza>",
            "email": "user-<id>"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "dest": "<same dest as current lab node>",
          "serverNames": ["<same serverName as Baza vpn_servers.server_name>"],
          "privateKey": "<node-local only>",
          "shortIds": ["<same short_id as Baza>"]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls", "quic"],
        "routeOnly": true
      }
    }
  ],
  "outbounds": [
    {"protocol": "freedom", "tag": "direct"},
    {"protocol": "blackhole", "tag": "block"}
  ]
}
```

For a production clone, omit the `8443` inbound. Add `flow` on the client only
if Happ has confirmed Vision.

Config file ownership on the lab node is `nobody:nogroup` mode `640`. Xray
runs as `nobody`; a root-only `600` file will fail at start.

## Backend row for a cloned node

```text
name          = <country code, e.g. DE>
country       = <country>
host          = <public IPv4 or hostname>
port          = 443
protocol      = vless
transport     = tcp
security      = reality
public_key    = <REALITY public key>
server_name   = <same SNI as the lab node unless a new dest is chosen>
short_id      = <allowed short ID>
fingerprint   = chrome
flow          = NULL
enabled       = true
status        = active
```

Export the user credential and add that UUID to the node:

```bash
python -m app.cli vpn export-user --user-id <id> --server-id <id> --json
```

## Happ checklist

Use the same steps for every matrix profile. Change one profile at a time.

1. Refresh the Baza subscription in Happ.
2. Select exactly one profile (`A`, `B`, `C`, or `D`).
3. Use Global / Proxy all / весь трафик.
4. Disable iCloud Private Relay and Limit IP Address Tracking.
5. Disconnect, then connect again.
6. Open `https://api.ipify.org`. The IP must equal the Germany node IPv4.
7. Open Google, then YouTube.
8. Confirm Xray access log has `accepted tcp:...` for that client email.

If Xray accepts traffic but the page hangs, check IPv6, QUIC/UDP, and Happ MTU
(try 1280-1400). Do not change SNI, UUID, and port at the same time.

## Disable losing variants

After Happ confirms a winner, disable the other `vpn_servers` rows:

```bash
docker compose exec -T app python /tmp/disable_non_canonical_profiles.py
```

The script keeps `A 443 no-flow` enabled. If another profile won, change
`CANONICAL_NAME` first. Losing inbounds can then be removed from Xray.

## Clone to the next VPS

1. Install the same Xray version as the lab node.
2. Copy the canonical inbound (port 443, no client `flow`).
3. Generate a new REALITY keypair on that VPS. Never reuse the lab private key.
4. Open `443/tcp` in the firewall. Confirm the VPS itself can reach the internet.
5. Insert one `vpn_servers` row with `flow=NULL` and `port=443`.
6. Export each test user and add their UUID to `clients`.
7. `xray run -test`, fix ownership, restart Xray.
8. Refresh Happ and run the checklist against `api.ipify.org`.

Do not:

- give each new VPS a different protocol mix;
- enable payments before one profile is stable;
- automate SSH provisioning in this MVP.
