from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import CB
from app.config import Settings
from app.enums import SubscriptionStatus, UserStatus
from app.models import Subscription, User


class MenuButton:
    CONNECT = "🛡 Подключить"
    SUBSCRIPTION = "💳 Подписка"
    DEVICES = "📱 Устройства"
    HELP = "ℹ️ Помощь"


MENU_BUTTON_TEXTS = {
    MenuButton.CONNECT,
    MenuButton.SUBSCRIPTION,
    MenuButton.DEVICES,
    MenuButton.HELP,
}


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MenuButton.CONNECT), KeyboardButton(text=MenuButton.SUBSCRIPTION)],
            [KeyboardButton(text=MenuButton.DEVICES), KeyboardButton(text=MenuButton.HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def welcome_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Попробовать бесплатно", callback_data=CB.START_TRIAL)
    )
    builder.row(InlineKeyboardButton(text="ℹ️ Как это работает", callback_data=CB.START_HOW))
    return builder.as_markup()


def how_it_works_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Попробовать бесплатно", callback_data=CB.START_TRIAL)
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()


def trial_ready_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📲 Подключить", callback_data=CB.CONNECT))
    builder.row(
        InlineKeyboardButton(text="📖 Как подключиться", callback_data=CB.CONNECT_INSTRUCTIONS)
    )
    return builder.as_markup()


def dashboard_keyboard(
    user: User,
    subscription: Subscription | None,
    settings: Settings,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if user.status == UserStatus.BLOCKED:
        if settings.support_url:
            builder.row(InlineKeyboardButton(text="💬 Поддержка", url=settings.support_url))
        else:
            builder.row(InlineKeyboardButton(text="💬 Поддержка", callback_data=CB.HELP_SUPPORT))
        return builder.as_markup()

    expired = subscription is None or subscription.status in {
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.CANCELLED,
    }

    if expired:
        builder.row(InlineKeyboardButton(text="💳 Продлить", callback_data=CB.SUBSCRIPTION_EXTEND))
        builder.row(
            InlineKeyboardButton(text="📱 Устройства", callback_data=CB.DEVICES),
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data=CB.HELP),
        )
        return builder.as_markup()

    builder.row(InlineKeyboardButton(text="📲 Подключить VPN", callback_data=CB.CONNECT))
    builder.row(
        InlineKeyboardButton(text="📱 Устройства", callback_data=CB.DEVICES),
        InlineKeyboardButton(
            text=(
                "💳 Управление подпиской"
                if subscription and subscription.status == SubscriptionStatus.ACTIVE
                else "💳 Подписка"
            ),
            callback_data=CB.SUBSCRIPTION,
        ),
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data=CB.HELP),
        InlineKeyboardButton(text="👤 Профиль", callback_data=CB.PROFILE),
    )
    return builder.as_markup()


def back_home_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()


def error_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if settings.support_url:
        builder.row(InlineKeyboardButton(text="💬 Поддержка", url=settings.support_url))
    else:
        builder.row(InlineKeyboardButton(text="💬 Поддержка", callback_data=CB.HELP_SUPPORT))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()
