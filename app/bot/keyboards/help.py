from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import CB
from app.config import Settings


def help_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📲 Не подключается", callback_data=CB.HELP_CONNECTION))
    builder.row(InlineKeyboardButton(text="🔗 Не добавляется ссылка", callback_data=CB.HELP_LINK))
    builder.row(InlineKeyboardButton(text="🐢 Медленно работает", callback_data=CB.HELP_SPEED))
    builder.row(InlineKeyboardButton(text="📱 Проблема с устройством", callback_data=CB.HELP_DEVICE))
    builder.row(InlineKeyboardButton(text="💬 Связаться с поддержкой", callback_data=CB.HELP_SUPPORT))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()


def help_topic_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Написать в поддержку", callback_data=CB.HELP_SUPPORT)
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HELP))
    return builder.as_markup()


def support_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if settings.support_url:
        builder.row(InlineKeyboardButton(text="💬 Написать в поддержку", url=settings.support_url))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HELP))
    return builder.as_markup()
