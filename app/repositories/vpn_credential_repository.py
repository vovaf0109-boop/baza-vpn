from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import VpnCredentialStatus
from app.models import VpnCredential


class VpnCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_by_user_server(
        self,
        user_id: int,
        server_id: int,
    ) -> VpnCredential | None:
        result = await self.session.execute(
            select(VpnCredential)
            .where(
                VpnCredential.user_id == user_id,
                VpnCredential.server_id == server_id,
            )
            .order_by(VpnCredential.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_active_by_user(self, user_id: int) -> list[VpnCredential]:
        result = await self.session.execute(
            select(VpnCredential)
            .where(
                VpnCredential.user_id == user_id,
                VpnCredential.status == VpnCredentialStatus.ACTIVE,
            )
            .order_by(VpnCredential.server_id.asc(), VpnCredential.id.asc())
        )
        return list(result.scalars().all())

    async def add(self, credential: VpnCredential) -> VpnCredential:
        self.session.add(credential)
        await self.session.flush()
        return credential
