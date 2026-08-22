from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot import texts
from app.bot.callbacks import CB
from app.bot.keyboards.subscription import checkout_keyboard, subscription_keyboard
from app.bot.navigation import safe_edit
from app.config import Settings
from app.exceptions import UserBlockedError
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService

router = Router()


@router.callback_query(F.data == CB.SUBSCRIPTION)
async def subscription_screen(
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
        await callback.answer("Сначала нажми «Попробовать бесплатно».", show_alert=True)
        return
    if user.is_blocked:
        await safe_edit(callback, texts.user_blocked(), checkout_keyboard(settings))
        await callback.answer()
        return

    subscription = await subscription_service.get_current(user)
    await safe_edit(
        callback,
        texts.subscription_screen(subscription, settings),
        subscription_keyboard(subscription),
    )
    await callback.answer()


@router.callback_query(F.data.in_({CB.SUBSCRIPTION_BUY, CB.SUBSCRIPTION_EXTEND}))
async def subscription_checkout(
    callback: CallbackQuery,
    user_service: UserService,
    payment_service: PaymentService,
    settings: Settings,
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

    try:
        await payment_service.start_checkout(user)
    except UserBlockedError:
        await safe_edit(callback, texts.user_blocked(), checkout_keyboard(settings))
        await callback.answer()
        return

    await safe_edit(callback, texts.checkout_unavailable(settings), checkout_keyboard(settings))
    await callback.answer()
