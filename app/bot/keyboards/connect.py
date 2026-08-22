from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import CB
from app.config import Settings


def connect_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if settings.happ_download_url:
        builder.row(
            InlineKeyboardButton(text="1️⃣ Скачать Happ", url=settings.happ_download_url)
        )
    builder.row(InlineKeyboardButton(text="2️⃣ Получить ссылку", callback_data=CB.CONNECT_GET_LINK))
    builder.row(InlineKeyboardButton(text="❓ Как подключиться", callback_data=CB.CONNECT_INSTRUCTIONS))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()


def link_keyboard(url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    copy_text = url[:256] if url else ""
    if copy_text:
        builder.row(
            InlineKeyboardButton(
                text="📋 Скопировать ссылку",
                copy_text=CopyTextButton(text=copy_text),
            )
        )
    builder.row(InlineKeyboardButton(text="📖 Инструкция", callback_data=CB.CONNECT_INSTRUCTIONS))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.CONNECT))
    return builder.as_markup()


def instructions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Позже сюда можно добавить: iPhone / Android / Windows / macOS
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.CONNECT))
    return builder.as_markup()
