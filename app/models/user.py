from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import UserStatus, enum_values
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.payment import Payment
    from app.models.subscription import Subscription
    from app.models.vpn_credential import VpnCredential


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'blocked')", name="ck_users_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    devices: Mapped[list["Device"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    vpn_credentials: Mapped[list["VpnCredential"]] = relationship(back_populates="user")

    @property
    def is_blocked(self) -> bool:
        return self.status == UserStatus.BLOCKED
