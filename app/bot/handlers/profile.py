from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot import texts
from app.bot.callbacks import CB
from app.bot.navigation import safe_edit
from app.services.device_service import DeviceService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService

router = Router()


def profile_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()


@router.callback_query(F.data == CB.PROFILE)
async def profile_screen(
    callback: CallbackQuery,
    user_service: UserService,
    subscription_service: SubscriptionService,
    device_service: DeviceService,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала нажми «Попробовать бесплатно».", show_alert=True)
        return

    subscription = await subscription_service.get_current(user)
    device_count = await device_service.count_active(user)
    await safe_edit(
        callback,
        texts.profile(user, subscription, device_count, device_service.limit),
        profile_keyboard(),
    )
    await callback.answer()


@router.message(Command("profile"))
async def profile_command(
    message: Message,
    user_service: UserService,
    subscription_service: SubscriptionService,
    device_service: DeviceService,
    state: FSMContext,
) -> None:
    await state.clear()
    if message.from_user is None:
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        return

    subscription = await subscription_service.get_current(user)
    device_count = await device_service.count_active(user)
    await message.answer(
        texts.profile(user, subscription, device_count, device_service.limit),
        reply_markup=profile_keyboard(),
    )
