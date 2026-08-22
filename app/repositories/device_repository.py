from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import DeviceStatus
from app.models import Device


class DeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: int, *, active_only: bool = False) -> list[Device]:
        stmt = select(Device).where(Device.user_id == user_id).order_by(Device.created_at.asc())
        if active_only:
            stmt = stmt.where(Device.status == DeviceStatus.ACTIVE)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Device)
            .where(Device.user_id == user_id, Device.status == DeviceStatus.ACTIVE)
        )
        return int(result.scalar_one())

    async def get_by_id(self, device_id: int) -> Device | None:
        result = await self.session.execute(select(Device).where(Device.id == device_id))
        return result.scalar_one_or_none()

    async def add(self, device: Device) -> Device:
        self.session.add(device)
        await self.session.flush()
        await self.session.refresh(device)
        return device
