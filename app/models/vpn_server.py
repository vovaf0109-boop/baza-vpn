from sqlalchemy import CheckConstraint, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import VpnServerStatus, enum_values
from app.models.base import Base, TimestampMixin


class VpnServer(TimestampMixin, Base):
    __tablename__ = "vpn_servers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'maintenance', 'disabled')",
            name="ck_vpn_servers_status",
        ),
        CheckConstraint("load >= 0", name="ck_vpn_servers_load_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[VpnServerStatus] = mapped_column(
        Enum(
            VpnServerStatus,
            name="vpn_server_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=VpnServerStatus.ACTIVE,
        nullable=False,
    )
    load: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
