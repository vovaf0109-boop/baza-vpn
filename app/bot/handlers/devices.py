from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot import texts
from app.bot.callbacks import CB
from app.bot.keyboards.devices import (
    device_limit_keyboard,
    devices_keyboard,
    manage_devices_keyboard,
)
from app.bot.navigation import safe_edit
from app.bot.states import DeviceStates
from app.exceptions import DeviceLimitReachedError, DeviceNotFoundError, UserBlockedError
from app.services.device_service import DeviceService
from app.services.user_service import UserService

router = Router()


@router.callback_query(F.data == CB.DEVICES)
async def devices_list(
    callback: CallbackQuery,
    user_service: UserService,
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

    devices = await device_service.list_active(user)
    await safe_edit(
        callback,
        texts.devices_screen(devices, device_service.limit),
        devices_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == CB.DEVICES_ADD)
async def devices_add(
    callback: CallbackQuery,
    user_service: UserService,
    device_service: DeviceService,
    state: FSMContext,
) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала нажми «Попробовать бесплатно».", show_alert=True)
        return
    if user.is_blocked:
        await safe_edit(callback, texts.user_blocked(), device_limit_keyboard())
        await callback.answer()
        return

    current = await device_service.count_active(user)
    if current >= device_service.limit:
        await safe_edit(
            callback,
            texts.device_limit_reached(current, device_service.limit),
            device_limit_keyboard(),
        )
        await callback.answer()
        return

    await state.set_state(DeviceStates.waiting_name)
    await safe_edit(callback, texts.ask_device_name(), device_limit_keyboard())
    await callback.answer()


@router.message(DeviceStates.waiting_name, F.text)
async def devices_add_name(
    message: Message,
    user_service: UserService,
    device_service: DeviceService,
    state: FSMContext,
) -> None:
    await state.clear()
    if message.from_user is None or not message.text:
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        return

    try:
        device = await device_service.add(user, message.text)
    except UserBlockedError:
        await message.answer(texts.user_blocked())
        return
    except DeviceLimitReachedError as exc:
        await message.answer(
            texts.device_limit_reached(exc.current, exc.limit),
            reply_markup=device_limit_keyboard(),
        )
        return

    devices = await device_service.list_active(user)
    await message.answer(texts.device_added(device.name))
    await message.answer(
        texts.devices_screen(devices, device_service.limit),
        reply_markup=devices_keyboard(),
    )


@router.callback_query(F.data == CB.DEVICES_MANAGE)
async def devices_manage(
    callback: CallbackQuery,
    user_service: UserService,
    device_service: DeviceService,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    devices = await device_service.list_active(user)
    await safe_edit(
        callback,
        texts.manage_devices(devices),
        manage_devices_keyboard(devices),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB.DEVICES_REVOKE_PREFIX))
async def devices_revoke(
    callback: CallbackQuery,
    user_service: UserService,
    device_service: DeviceService,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.from_user is None or not callback.data:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    device_id = CB.parse_revoke_device(callback.data)
    if device_id is None:
        await callback.answer()
        return

    try:
        device = await device_service.revoke(user, device_id)
        await callback.answer(texts.device_revoked(device.name))
    except DeviceNotFoundError:
        await callback.answer("Устройство уже отключено.")

    devices = await device_service.list_active(user)
    await safe_edit(
        callback,
        texts.devices_screen(devices, device_service.limit),
        devices_keyboard(),
    )
