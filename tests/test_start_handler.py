import pytest
from sqlalchemy import func, select

from app.bot.callbacks import CB
from app.bot.handlers import fallback, setup_routers, start
from app.bot.handlers.fallback import unknown_callback
from app.bot.handlers.start import cmd_start, start_how, start_trial
from app.bot.keyboards.main import welcome_keyboard
from app.bot.texts import how_it_works, trial_ready, welcome
from app.config import Settings
from app.models import Subscription
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


class DummyCallbackMessage:
    def __init__(self) -> None:
        self.edits: list[tuple[str, object | None, str | None]] = []
        self.answers: list[tuple[str, object | None]] = []

    async def edit_text(
        self,
        text: str,
        reply_markup: object | None = None,
        parse_mode: str | None = None,
    ) -> None:
        self.edits.append((text, reply_markup, parse_mode))

    async def answer(
        self,
        text: str,
        reply_markup: object | None = None,
        **_: object,
    ) -> None:
        self.answers.append((text, reply_markup))


class DummyCallback:
    def __init__(self, data: str, from_user: DummyTelegramUser) -> None:
        self.data = data
        self.from_user = from_user
        self.message = DummyCallbackMessage()
        self.answers: list[tuple[str | None, bool | None]] = []

    async def answer(self, text: str | None = None, show_alert: bool | None = None) -> None:
        self.answers.append((text, show_alert))


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


def test_welcome_keyboard_callback_data_matches_start_callbacks() -> None:
    markup = welcome_keyboard()

    assert markup.inline_keyboard[0][0].callback_data == CB.START_TRIAL
    assert markup.inline_keyboard[1][0].callback_data == CB.START_HOW


def test_fallback_router_is_registered_after_valid_callback_routers() -> None:
    router = setup_routers()

    assert router.observers["callback_query"].handlers == []
    assert start.router in router.sub_routers
    assert fallback.router in router.sub_routers
    assert router.sub_routers.index(start.router) < router.sub_routers.index(fallback.router)
    assert router.sub_routers[-1] is fallback.router


@pytest.mark.asyncio
async def test_start_how_callback_shows_instruction(settings: Settings) -> None:
    callback = DummyCallback(CB.START_HOW, DummyTelegramUser(7101, "user", "User"))

    await start_how(callback, settings)  # type: ignore[arg-type]

    assert callback.message.edits[0][0] == how_it_works(settings)
    assert callback.answers == [(None, None)]


@pytest.mark.asyncio
async def test_start_trial_callback_creates_trial_and_not_stale(
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> None:
    callback = DummyCallback(CB.START_TRIAL, DummyTelegramUser(7102, "trial", "Trial"))

    await start_trial(
        callback,  # type: ignore[arg-type]
        user_service,
        subscription_service,
        settings,
        DummyState(),  # type: ignore[arg-type]
    )

    user = await user_service.get_by_telegram_id(7102)
    assert user is not None
    subscription = await subscription_service.get_current(user)
    assert subscription is not None
    assert callback.message.edits[0][0] == trial_ready(settings)
    assert callback.answers == [(None, None)]
    assert all(answer[0] != "Кнопка устарела. Открой меню ещё раз." for answer in callback.answers)


@pytest.mark.asyncio
async def test_unknown_callback_is_handled_safely() -> None:
    callback = DummyCallback("unknown_callback", DummyTelegramUser(7103, "user", "User"))

    await unknown_callback(callback)  # type: ignore[arg-type]

    assert callback.answers == [("Кнопка устарела. Открой меню ещё раз.", True)]


@pytest.mark.asyncio
async def test_repeat_start_after_trial_shows_dashboard(
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
    session,
) -> None:
    callback = DummyCallback(CB.START_TRIAL, DummyTelegramUser(7104, "trial", "Trial"))
    await start_trial(
        callback,  # type: ignore[arg-type]
        user_service,
        subscription_service,
        settings,
        DummyState(),  # type: ignore[arg-type]
    )

    second_start = DummyMessage(DummyTelegramUser(7104, "trial2", "Trial Two"))
    await cmd_start(
        second_start,  # type: ignore[arg-type]
        user_service,
        subscription_service,
        settings,
        DummyState(),  # type: ignore[arg-type]
    )

    total = await session.scalar(select(func.count()).select_from(Subscription))
    assert total == 1
    assert "VPN доступен" in second_start.answers[0][0]


@pytest.mark.asyncio
async def test_start_trial_callback_cannot_create_trial_twice(
    monkeypatch: pytest.MonkeyPatch,
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
    session,
) -> None:
    first = DummyCallback(CB.START_TRIAL, DummyTelegramUser(7105, "trial", "Trial"))
    await start_trial(
        first,  # type: ignore[arg-type]
        user_service,
        subscription_service,
        settings,
        DummyState(),  # type: ignore[arg-type]
    )

    dashboard_calls = 0

    async def fake_show_main_menu(*args: object, **kwargs: object) -> None:
        nonlocal dashboard_calls
        dashboard_calls += 1

    monkeypatch.setattr("app.bot.handlers.start.show_main_menu", fake_show_main_menu)

    second = DummyCallback(CB.START_TRIAL, DummyTelegramUser(7105, "trial", "Trial"))
    await start_trial(
        second,  # type: ignore[arg-type]
        user_service,
        subscription_service,
        settings,
        DummyState(),  # type: ignore[arg-type]
    )

    total = await session.scalar(select(func.count()).select_from(Subscription))
    assert total == 1
    assert dashboard_calls == 1
