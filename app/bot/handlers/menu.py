from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot import texts
from app.bot.keyboards.connect import connect_keyboard
from app.bot.keyboards.devices import devices_keyboard
from app.bot.keyboards.help import help_keyboard
from app.bot.keyboards.main import MenuButton, welcome_keyboard
from app.bot.keyboards.subscription import subscription_keyboard
from app.bot.navigation import show_main_menu
from app.config import Settings
from app.services.device_service import DeviceService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService

router = Router()


async def require_user(
    message: Message,
    user_service: UserService,
    settings: Settings,
):
    if message.from_user is None:
        return None
    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(texts.welcome(settings), reply_markup=welcome_keyboard())
        return None
    return user


@router.message(F.text == MenuButton.CONNECT)
async def menu_connect(
    message: Message,
    user_service: UserService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    user = await require_user(message, user_service, settings)
    if user is None:
        return
    if user.is_blocked:
        await message.answer(texts.user_blocked())
        return
    await message.answer(texts.connect_screen(), reply_markup=connect_keyboard(settings))


@router.message(F.text == MenuButton.SUBSCRIPTION)
async def menu_subscription(
    message: Message,
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    user = await require_user(message, user_service, settings)
    if user is None:
        return
    if user.is_blocked:
        await message.answer(texts.user_blocked())
        return
    subscription = await subscription_service.get_current(user)
    await message.answer(
        texts.subscription_screen(subscription, settings),
        reply_markup=subscription_keyboard(subscription),
    )


@router.message(F.text == MenuButton.DEVICES)
async def menu_devices(
    message: Message,
    user_service: UserService,
    device_service: DeviceService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    user = await require_user(message, user_service, settings)
    if user is None:
        return
    if user.is_blocked:
        await message.answer(texts.user_blocked())
        return
    devices = await device_service.list_active(user)
    await message.answer(
        texts.devices_screen(devices, device_service.limit),
        reply_markup=devices_keyboard(),
    )


@router.message(F.text == MenuButton.HELP)
async def menu_help(
    message: Message,
    user_service: UserService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    user = await require_user(message, user_service, settings)
    if user is None:
        return
    await message.answer(texts.help_home(), reply_markup=help_keyboard())


@router.message(F.text == "🏠 Меню")
async def menu_home(
    message: Message,
    user_service: UserService,
    subscription_service: SubscriptionService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    user = await require_user(message, user_service, settings)
    if user is None:
        return
    await show_main_menu(
        message,
        user,
        subscription_service,
        settings,
        with_reply_keyboard=True,
    )
