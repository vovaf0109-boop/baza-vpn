from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import VpnServerStatus, enum_values
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.vpn_credential import VpnCredential


class VpnServer(TimestampMixin, Base):
    __tablename__ = "vpn_servers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'maintenance', 'disabled')",
            name="ck_vpn_servers_status",
        ),
        CheckConstraint("load >= 0", name="ck_vpn_servers_load_non_negative"),
        CheckConstraint("port IS NULL OR (port > 0 AND port <= 65535)", name="ck_vpn_servers_port"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str] = mapped_column(String(16), default="vless", nullable=False)
    transport: Mapped[str] = mapped_column(String(16), default="tcp", nullable=False)
    security: Mapped[str] = mapped_column(String(16), default="reality", nullable=False)
    public_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    server_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(32), default="chrome", nullable=False)
    flow: Mapped[str | None] = mapped_column(String(64), default="xtls-rprx-vision", nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
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

    credentials: Mapped[list["VpnCredential"]] = relationship(back_populates="server")
