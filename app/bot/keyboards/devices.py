from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import CB
from app.models import Device


def devices_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить устройство", callback_data=CB.DEVICES_ADD))
    builder.row(
        InlineKeyboardButton(text="🗑 Управление устройствами", callback_data=CB.DEVICES_MANAGE)
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()


def manage_devices_keyboard(devices: list[Device]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for device in devices:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {device.name}",
                callback_data=CB.revoke_device(device.id),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.DEVICES))
    return builder.as_markup()


def device_limit_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📱 Мои устройства", callback_data=CB.DEVICES))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()
