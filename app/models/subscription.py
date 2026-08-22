from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SubscriptionStatus, enum_values
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('trial', 'active', 'expired', 'cancelled')",
            name="ck_subscriptions_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(
            SubscriptionStatus,
            name="subscription_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=SubscriptionStatus.TRIAL,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trial_used: Mapped[bool] = mapped_column(default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="subscription")

    def is_usable(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return (
            self.status in {SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE}
            and expires > now
        )

    @property
    def is_trial(self) -> bool:
        return self.status == SubscriptionStatus.TRIAL

    @property
    def plan_title(self) -> str:
        if self.status == SubscriptionStatus.TRIAL:
            return "Бесплатный период"
        if self.status == SubscriptionStatus.ACTIVE:
            return "Premium"
        return "Нет подписки"
