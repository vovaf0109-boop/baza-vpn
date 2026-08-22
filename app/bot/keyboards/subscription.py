from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import CB
from app.config import Settings
from app.enums import SubscriptionStatus
from app.models import Subscription


def subscription_keyboard(subscription: Subscription | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    expired = subscription is None or subscription.status in {
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.CANCELLED,
    }
    if expired or (subscription and subscription.status == SubscriptionStatus.TRIAL):
        builder.row(
            InlineKeyboardButton(text="💳 Оформить подписку", callback_data=CB.SUBSCRIPTION_BUY)
        )
    else:
        builder.row(InlineKeyboardButton(text="🔄 Продлить", callback_data=CB.SUBSCRIPTION_EXTEND))
        builder.row(InlineKeyboardButton(text="📱 Устройства", callback_data=CB.DEVICES))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.HOME))
    return builder.as_markup()


def checkout_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if settings.support_url:
        builder.row(InlineKeyboardButton(text="💬 Написать в поддержку", url=settings.support_url))
    else:
        builder.row(
            InlineKeyboardButton(text="💬 Написать в поддержку", callback_data=CB.HELP_SUPPORT)
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CB.SUBSCRIPTION))
    return builder.as_markup()
