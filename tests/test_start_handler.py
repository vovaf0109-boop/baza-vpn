import pytest

from app.bot.handlers.start import cmd_start
from app.bot.texts import welcome
from app.config import Settings
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService


class DummyTelegramUser:
    def __init__(self, user_id: int, username: str | None, first_name: str | None) -> None:
        self.id = user_id
        self.username = username
        self.first_name = first_name


class DummyMessage:
    def __init__(self, from_user: DummyTelegramUser) -> None:
        self.from_user = from_user
        self.answers: list[tuple[str, object | None]] = []

    async def answer(self, text: str, reply_markup: object | None = None) -> None:
        self.answers.append((text, reply_markup))


class DummyState:
    def __init__(self) -> None:
        self.cleared = False

    async def clear(self) -> None:
        self.cleared = True


@pytest.mark.asyncio
async def test_start_creates_user_once(
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> None:
    first_message = DummyMessage(DummyTelegramUser(7001, "first", "First"))
    await cmd_start(
        first_message,  # type: ignore[arg-type]
        user_service,
        subscription_service,
        settings,
        DummyState(),  # type: ignore[arg-type]
    )

    created = await user_service.get_by_telegram_id(7001)
    assert created is not None
    assert created.username == "first"
    assert first_message.answers[0][0] == welcome(settings)

    second_message = DummyMessage(DummyTelegramUser(7001, "second", "Second"))
    await cmd_start(
        second_message,  # type: ignore[arg-type]
        user_service,
        subscription_service,
        settings,
        DummyState(),  # type: ignore[arg-type]
    )

    same_user = await user_service.get_by_telegram_id(7001)
    assert same_user is not None
    assert same_user.id == created.id
    assert same_user.username == "second"
    assert same_user.first_name == "Second"
