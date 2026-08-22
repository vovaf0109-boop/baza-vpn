from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import DeviceStatus, enum_values
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Device(TimestampMixin, Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("user_id", "identifier", name="uq_device_user_identifier"),
        CheckConstraint("status IN ('active', 'revoked')", name="ck_devices_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(
            DeviceStatus,
            name="device_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=DeviceStatus.ACTIVE,
        nullable=False,
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="devices")

    @property
    def active(self) -> bool:
        return self.status == DeviceStatus.ACTIVE
