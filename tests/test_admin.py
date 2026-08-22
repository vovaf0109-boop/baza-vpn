import pytest

from app.bot.handlers.admin import _is_admin, admin_extend
from app.config import Settings


class DummyTelegramUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class DummyMessage:
    def __init__(self, user_id: int) -> None:
        self.from_user = DummyTelegramUser(user_id)
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


class DummyCommand:
    def __init__(self, args: str | None) -> None:
        self.args = args


class UnusedAdminService:
    async def find_user(self, raw: str):  # pragma: no cover - should not be called
        raise AssertionError("admin service should not be called for invalid input")


def test_admin_authorization_uses_telegram_id_only() -> None:
    settings = Settings(app_env="test", admin_telegram_ids="42")

    assert _is_admin(DummyMessage(42), settings) is True  # type: ignore[arg-type]
    assert _is_admin(DummyMessage(43), settings) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_admin_extend_rejects_too_many_days() -> None:
    settings = Settings(
        app_env="test",
        admin_telegram_ids="42",
        admin_max_extend_days=30,
    )
    message = DummyMessage(42)

    await admin_extend(
        message,  # type: ignore[arg-type]
        DummyCommand("123 999"),  # type: ignore[arg-type]
        settings,
        UnusedAdminService(),  # type: ignore[arg-type]
    )

    assert message.answers == ["Количество дней должно быть от 1 до 30."]
