"""Disable lab matrix profiles that are not the canonical MVP template.

Canonical profile is A: 443/tcp, VLESS+REALITY, no flow.
"""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import create_engine
from app.models import VpnServer

CANONICAL_NAME = "A 443 no-flow"
MATRIX_NAMES = (
    "A 443 no-flow",
    "B 443 vision",
    "C 8443 no-flow",
    "D 8443 vision",
)


async def main() -> None:
    engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            servers = list(
                (
                    await session.execute(select(VpnServer).where(VpnServer.name.in_(MATRIX_NAMES)))
                ).scalars()
            )
            result = []
            for server in servers:
                enabled = server.name == CANONICAL_NAME
                server.enabled = enabled
                result.append({"enabled": enabled, "name": server.name, "port": server.port, "server_id": server.id})
            await session.commit()
            print(json.dumps(result, sort_keys=True))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
