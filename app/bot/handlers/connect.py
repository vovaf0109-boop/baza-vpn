from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot import texts
from app.bot.callbacks import CB
from app.bot.content.guides import guide_text
from app.bot.keyboards.connect import connect_keyboard, instructions_keyboard, link_keyboard
from app.bot.keyboards.subscription import subscription_keyboard
from app.bot.navigation import safe_edit
from app.config import Settings
from app.exceptions import DeviceLimitReachedError, SubscriptionInactiveError, UserBlockedError
from app.services.device_service import DeviceService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.vpn_service import VpnService

router = Router()


@router.callback_query(F.data == CB.CONNECT)
async def connect_screen(
    callback: CallbackQuery,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    await safe_edit(callback, texts.connect_screen(), connect_keyboard(settings))
    await callback.answer()


@router.callback_query(F.data == CB.CONNECT_INSTRUCTIONS)
async def connect_instructions(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, guide_text("general"), instructions_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.CONNECT_GET_LINK)
async def connect_get_link(
    callback: CallbackQuery,
    user_service: UserService,
    subscription_service: SubscriptionService,
    device_service: DeviceService,
    vpn_service: VpnService,
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
        url = await vpn_service.get_connection_url(user)
        try:
            await device_service.get_or_create_default(user)
        except DeviceLimitReachedError:
            pass
    except UserBlockedError:
        await safe_edit(callback, texts.user_blocked(), connect_keyboard(settings))
        await callback.answer()
        return
    except SubscriptionInactiveError:
        subscription = await subscription_service.get_current(user)
        await safe_edit(
            callback,
            texts.subscription_inactive(),
            subscription_keyboard(subscription),
        )
        await callback.answer()
        return

    await safe_edit(
        callback,
        texts.connection_link(url, bool(settings.subscription_base_url)),
        link_keyboard(url if settings.subscription_base_url else ""),
    )
    await callback.answer()
