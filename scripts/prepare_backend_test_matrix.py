"""Upsert the A-D lab matrix as VpnServer + VpnCredential rows.

Intended to run inside the backend app container. Prints only ids and hashes.
Existing servers on the lab host are reused by (port, flow), then renamed.
Any other enabled server on the same host is disabled so Happ sees only A-D.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import create_engine
from app.enums import VpnCredentialStatus, VpnServerStatus
from app.models import VpnCredential, VpnServer

USER_ID = 1
SOURCE_PORT = 8443
VISION_FLOW = "xtls-rprx-vision"
MATRIX = (
    {"code": "A", "name": "A 443 no-flow", "port": 443, "flow": None},
    {"code": "B", "name": "B 443 vision", "port": 443, "flow": VISION_FLOW},
    {"code": "C", "name": "C 8443 no-flow", "port": 8443, "flow": None},
    {"code": "D", "name": "D 8443 vision", "port": 8443, "flow": VISION_FLOW},
)


def _sha12(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def _flow_key(value: str | None) -> str:
    return value or ""


async def main() -> None:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            source = (
                await session.execute(select(VpnServer).where(VpnServer.port == SOURCE_PORT).order_by(VpnServer.id))
            ).scalars().first()
            if source is None:
                raise SystemExit("source vpn server not found")

            host = source.host
            existing = list((await session.execute(select(VpnServer).where(VpnServer.host == host))).scalars())
            used_ids: set[int] = set()
            by_name = {server.name: server for server in existing}
            by_port_flow: dict[tuple[int, str], VpnServer] = {}
            for server in existing:
                key = (server.port or 0, _flow_key(server.flow))
                by_port_flow.setdefault(key, server)

            rows = []
            for item in MATRIX:
                server = by_name.get(item["name"])
                if server is None:
                    server = by_port_flow.get((item["port"], _flow_key(item["flow"])))
                    if server is not None and server.id in used_ids:
                        server = None
                if server is None:
                    server = VpnServer(
                        name=item["name"],
                        country=source.country,
                        host=host,
                        port=item["port"],
                        protocol=source.protocol,
                        transport=source.transport,
                        security=source.security,
                        public_key=source.public_key,
                        server_name=source.server_name,
                        short_id=source.short_id,
                        fingerprint=source.fingerprint,
                        flow=item["flow"],
                        status=VpnServerStatus.ACTIVE,
                        load=source.load,
                        enabled=True,
                    )
                    session.add(server)
                    await session.flush()
                else:
                    server.name = item["name"]
                    server.host = host
                    server.country = source.country
                    server.port = item["port"]
                    server.protocol = source.protocol
                    server.transport = source.transport
                    server.security = source.security
                    server.public_key = source.public_key
                    server.server_name = source.server_name
                    server.short_id = source.short_id
                    server.fingerprint = source.fingerprint
                    server.flow = item["flow"]
                    server.status = VpnServerStatus.ACTIVE
                    server.enabled = True
                used_ids.add(server.id)

                credential = (
                    await session.execute(
                        select(VpnCredential).where(
                            VpnCredential.user_id == USER_ID,
                            VpnCredential.server_id == server.id,
                            VpnCredential.status == VpnCredentialStatus.ACTIVE,
                        )
                    )
                ).scalars().first()
                created = False
                if credential is None:
                    credential = VpnCredential(
                        user_id=USER_ID,
                        server_id=server.id,
                        credential_id=str(uuid.uuid4()),
                        status=VpnCredentialStatus.ACTIVE,
                    )
                    session.add(credential)
                    created = True
                rows.append(
                    {
                        "code": item["code"],
                        "created_credential": created,
                        "credential_id": credential.credential_id,
                        "credential_sha256_12": _sha12(credential.credential_id),
                        "has_flow": bool(item["flow"]),
                        "name": server.name,
                        "port": server.port,
                        "server_id": server.id,
                    }
                )

            no_flow_names = [item["name"] for item in MATRIX if item["flow"] is None]
            if no_flow_names:
                await session.execute(update(VpnServer).where(VpnServer.name.in_(no_flow_names)).values(flow=None))

            disabled = []
            leftover = list((await session.execute(select(VpnServer).where(VpnServer.host == host))).scalars())
            for server in leftover:
                if server.id in used_ids:
                    continue
                if server.enabled:
                    server.enabled = False
                    disabled.append({"name": server.name, "server_id": server.id})

            await session.commit()
            print(json.dumps({"disabled_extra": disabled, "matrix": rows}, sort_keys=True))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
