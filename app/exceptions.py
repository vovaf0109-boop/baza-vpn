class DomainError(Exception):
    """Ошибка бизнес-логики, безопасная для показа пользователю."""


class UserBlockedError(DomainError):
    pass


class TrialAlreadyUsedError(DomainError):
    pass


class SubscriptionInactiveError(DomainError):
    pass


class DeviceLimitReachedError(DomainError):
    def __init__(self, current: int, limit: int) -> None:
        self.current = current
        self.limit = limit
        super().__init__(f"device limit reached: {current}/{limit}")


class DeviceNotFoundError(DomainError):
    pass


class PaymentNotFoundError(DomainError):
    pass


class PaymentAlreadyProcessedError(DomainError):
    pass
