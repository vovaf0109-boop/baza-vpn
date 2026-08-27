from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot import texts
from app.bot.callbacks import CB
from app.bot.keyboards.main import (
    how_it_works_keyboard,
    trial_ready_keyboard,
    welcome_keyboard,
)
from app.bot.navigation import safe_edit, show_main_menu
from app.config import Settings
from app.exceptions import TrialAlreadyUsedError, UserBlockedError
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService

router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    if message.from_user is None:
        return

    user = await user_service.create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    if user.is_blocked:
        await show_main_menu(
            message,
            user,
            subscription_service,
            settings,
            with_reply_keyboard=True,
        )
        return

    subscription = await subscription_service.get_current(user)
    if subscription is None:
        await message.answer(texts.welcome(settings), reply_markup=welcome_keyboard())
        return

    await show_main_menu(
        message,
        user,
        subscription_service,
        settings,
        with_reply_keyboard=True,
    )


@router.callback_query(F.data == CB.START_HOW)
async def start_how(callback: CallbackQuery, settings: Settings) -> None:
    await safe_edit(callback, texts.how_it_works(settings), how_it_works_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.START_TRIAL)
async def start_trial(
    callback: CallbackQuery,
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return

    user = await user_service.create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )
    try:
        await subscription_service.create_trial(user)
    except UserBlockedError:
        await safe_edit(callback, texts.user_blocked(), None)
        await callback.answer()
        return
    except TrialAlreadyUsedError:
        await show_main_menu(callback, user, subscription_service, settings, state=state)
        return

    await safe_edit(callback, texts.trial_ready(settings), trial_ready_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.HOME)
async def home(
    callback: CallbackQuery,
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await safe_edit(callback, texts.welcome(settings), welcome_keyboard())
        await callback.answer()
        return

    await show_main_menu(callback, user, subscription_service, settings)
