from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot import texts
from app.bot.keyboards.main import dashboard_keyboard, main_reply_keyboard
from app.config import Settings
from app.models import User
from app.services.subscription_service import SubscriptionService


async def show_main_menu(
    target: Message | CallbackQuery,
    user: User,
    subscription_service: SubscriptionService,
    settings: Settings,
    *,
    state: FSMContext | None = None,
    with_reply_keyboard: bool = False,
) -> None:
    if state is not None:
        await state.clear()

    subscription = await subscription_service.get_current(user)
    text = texts.dashboard(user, subscription, settings)
    inline = dashboard_keyboard(user, subscription, settings)

    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, inline)
        await target.answer()
        return

    markup = main_reply_keyboard() if with_reply_keyboard else inline
    if with_reply_keyboard:
        await target.answer(text, reply_markup=markup)
        return
    await target.answer(text, reply_markup=inline)


async def safe_edit(
    callback: CallbackQuery,
    text: str,
    markup: InlineKeyboardMarkup | None,
    *,
    parse_mode: str = "HTML",
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode=parse_mode)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=markup, parse_mode=parse_mode)
