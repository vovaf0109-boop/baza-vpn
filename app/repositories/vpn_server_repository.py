from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import VpnServerStatus
from app.models import VpnServer


class VpnServerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[VpnServer]:
        result = await self.session.execute(select(VpnServer).order_by(VpnServer.id.asc()))
        return list(result.scalars().all())

    async def list_available(self) -> list[VpnServer]:
        result = await self.session.execute(
            select(VpnServer)
            .where(
                VpnServer.enabled.is_(True),
                VpnServer.status == VpnServerStatus.ACTIVE,
            )
            .order_by(VpnServer.load.asc(), VpnServer.id.asc())
        )
        return list(result.scalars().all())
