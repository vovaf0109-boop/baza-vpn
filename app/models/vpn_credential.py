from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import VpnCredentialStatus, enum_values
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vpn_server import VpnServer


class VpnCredential(TimestampMixin, Base):
    __tablename__ = "vpn_credentials"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'revoked')", name="ck_vpn_credentials_status"),
        Index("ix_vpn_credentials_user_server_status", "user_id", "server_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("vpn_servers.id"), index=True)
    credential_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    status: Mapped[VpnCredentialStatus] = mapped_column(
        Enum(
            VpnCredentialStatus,
            name="vpn_credential_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=VpnCredentialStatus.ACTIVE,
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="vpn_credentials")
    server: Mapped["VpnServer"] = relationship(back_populates="credentials")
