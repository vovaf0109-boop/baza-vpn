from enum import StrEnum
from typing import TypeVar


EnumT = TypeVar("EnumT", bound=StrEnum)


def enum_values(enum_cls: type[EnumT]) -> list[str]:
    return [item.value for item in enum_cls]


class UserStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class SubscriptionStatus(StrEnum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DeviceStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class VpnServerStatus(StrEnum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class PaymentProviderName(StrEnum):
    STUB = "stub"
    TELEGRAM_STARS = "telegram_stars"
