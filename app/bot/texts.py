from app.config import Settings
from app.enums import SubscriptionStatus, UserStatus
from app.models import Device, Subscription, User
from app.utils.datetime import format_date_ru, format_remaining
from app.utils.html import html_escape
from app.utils.text import plural_ru


def welcome(settings: Settings) -> str:
    return (
        f"🛡 Добро пожаловать в {settings.app_name}\n"
        "\n"
        "VPN, который просто работает.\n"
        "\n"
        "Без сложных настроек:\n"
        "подключился → открыл нужное приложение → готово.\n"
        "\n"
        f"🎁 Новым пользователям — {settings.trial_days} дней бесплатно."
    )


def how_it_works(settings: Settings) -> str:
    return (
        "ℹ️ Как это работает\n"
        "\n"
        f"1. Получаешь {settings.trial_days} дней бесплатно.\n"
        "2. Устанавливаешь Happ.\n"
        "3. Добавляешь ссылку подключения.\n"
        "4. Включаешь VPN.\n"
        "\n"
        "Всё. Больше ничего настраивать не нужно."
    )


def trial_ready(settings: Settings) -> str:
    return (
        "🎉 Готово!\n"
        "\n"
        f"Тебе доступно {settings.trial_days} дней бесплатно.\n"
        "\n"
        "Теперь осталось подключить VPN."
    )


def dashboard(user: User, subscription: Subscription | None, settings: Settings) -> str:
    if user.status == UserStatus.BLOCKED:
        return (
            f"🛡 {settings.app_name}\n"
            "\n"
            "🚫 Доступ ограничен\n"
            "\n"
            "Если это ошибка — напиши в поддержку."
        )

    if subscription is None or subscription.status in {
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.CANCELLED,
    }:
        return (
            f"🛡 {settings.app_name}\n"
            "\n"
            "🔴 Подписка закончилась\n"
            "\n"
            "Возобнови подписку, чтобы снова пользоваться VPN."
        )

    if subscription.status == SubscriptionStatus.TRIAL:
        return (
            f"🛡 {settings.app_name}\n"
            "\n"
            "🟢 VPN доступен\n"
            "\n"
            "Тариф:\n"
            "Бесплатный период\n"
            "\n"
            "Осталось:\n"
            f"{format_remaining(subscription.expires_at)}"
        )

    return (
        f"🛡 {settings.app_name}\n"
        "\n"
        "🟢 Подписка активна\n"
        "\n"
        "Действует до:\n"
        f"{format_date_ru(subscription.expires_at)}"
    )


def connect_screen() -> str:
    return (
        "📲 Подключение\n"
        "\n"
        "Чтобы пользоваться VPN, установи приложение Happ.\n"
        "\n"
        "После установки добавь в него свою ссылку подключения."
    )


def connection_link(url: str, configured: bool) -> str:
    safe_url = html_escape(url)
    extra = ""
    if not configured:
        extra = (
            "\n\n⚠️ Ссылка ещё не настроена полностью.\n"
            "Нужно указать SUBSCRIPTION_BASE_URL в конфигурации."
        )
    return (
        "🔗 Твоя ссылка подключения\n"
        "\n"
        "Скопируй её и добавь в Happ.\n"
        "\n"
        f"<code>{safe_url}</code>"
        f"{extra}"
    )


def subscription_screen(
    subscription: Subscription | None,
    settings: Settings,
) -> str:
    price = f"{settings.subscription_price_rub} ₽ / месяц"

    if subscription is None or subscription.status in {
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.CANCELLED,
    }:
        return (
            "💳 Подписка\n"
            "\n"
            "Сейчас VPN недоступен.\n"
            "\n"
            f"Стоимость:\n{price}"
        )

    if subscription.status == SubscriptionStatus.TRIAL:
        return (
            "💳 Подписка\n"
            "\n"
            "🎁 Бесплатный период\n"
            "\n"
            "Осталось:\n"
            f"{format_remaining(subscription.expires_at)}\n"
            "\n"
            "После окончания:\n"
            f"{price}"
        )

    return (
        "💳 Подписка\n"
        "\n"
        "💳 Premium\n"
        "\n"
        "Стоимость:\n"
        f"{price}\n"
        "\n"
        "Действует до:\n"
        f"{format_date_ru(subscription.expires_at)}"
    )


def checkout_unavailable(settings: Settings) -> str:
    return (
        "💳 Оформить подписку\n"
        "\n"
        f"Premium — {settings.subscription_price_rub} ₽ / месяц\n"
        "\n"
        "Онлайн-оплата ещё подключается.\n"
        "Напиши в поддержку — поможем оформить вручную."
    )


def devices_screen(devices: list[Device], limit: int) -> str:
    if not devices:
        body = "Пока нет устройств.\nДобавь первое, чтобы было проще следить за подключениями."
    else:
        rows = []
        for device in devices:
            rows.append(f"📱 {html_escape(device.name)}\n🟢 Активно")
        body = "\n\n".join(rows)

    return (
        "📱 Мои устройства\n"
        "\n"
        f"{body}\n"
        "\n"
        f"{len(devices)} / {limit} "
        f"{plural_ru(limit, 'устройство', 'устройства', 'устройств')}"
    )


def device_limit_reached(current: int, limit: int) -> str:
    return (
        "⚠️ Достигнут лимит устройств.\n"
        "\n"
        "Сейчас подключено:\n"
        f"{current} из {limit}.\n"
        "\n"
        "Отключи одно из устройств или увеличь лимит тарифа."
    )


def ask_device_name() -> str:
    return (
        "➕ Новое устройство\n"
        "\n"
        "Как его назвать?\n"
        "Например: iPhone или Ноутбук."
    )


def device_added(name: str) -> str:
    return f"Готово. Устройство «{html_escape(name)}» добавлено."


def device_revoked(name: str) -> str:
    return f"Устройство «{html_escape(name)}» отключено."


def manage_devices(devices: list[Device]) -> str:
    if not devices:
        return "Нет активных устройств, которые можно отключить."
    return (
        "🗑 Управление устройствами\n"
        "\n"
        "Нажми на устройство, чтобы отключить его."
    )


def profile(user: User, subscription: Subscription | None, device_count: int, limit: int) -> str:
    if user.is_blocked:
        status = "🚫 Ограничен"
        plan = "—"
        until = "—"
    elif subscription is None or not subscription.is_usable():
        status = "🔴 Неактивен"
        plan = "Нет подписки"
        until = "—"
    else:
        status = "🟢 Активен"
        plan = subscription.plan_title
        until = format_date_ru(subscription.expires_at)

    return (
        "👤 Профиль\n"
        "\n"
        f"ID: #{user.id}\n"
        "\n"
        "Статус:\n"
        f"{status}\n"
        "\n"
        "Тариф:\n"
        f"{plan}\n"
        "\n"
        "До:\n"
        f"{until}\n"
        "\n"
        "Устройства:\n"
        f"{device_count} / {limit}"
    )


def help_home() -> str:
    return "ℹ️ Помощь\n\nЧто произошло?"


def help_connection() -> str:
    return (
        "📲 Не подключается\n"
        "\n"
        "Попробуй:\n"
        "\n"
        "1. Убедиться, что Happ установлен.\n"
        "2. Ещё раз добавить ссылку подключения.\n"
        "3. Обновить подписку в приложении.\n"
        "4. Выбрать сервер и включить VPN.\n"
        "\n"
        "Если не помогло — напиши в поддержку."
    )


def help_link() -> str:
    return (
        "🔗 Не добавляется ссылка\n"
        "\n"
        "Попробуй:\n"
        "\n"
        "1. Скопировать ссылку целиком.\n"
        "2. Открыть Happ → добавление подписки.\n"
        "3. Вставить ссылку и подтвердить.\n"
        "4. Обновить подписку.\n"
        "\n"
        "Если не помогло — напиши в поддержку."
    )


def help_speed() -> str:
    return (
        "🐢 VPN работает медленно\n"
        "\n"
        "Попробуй:\n"
        "\n"
        "1. Обновить подписку в Happ.\n"
        "2. Выбрать другой сервер.\n"
        "3. Переподключить VPN.\n"
        "4. Проверить работу через несколько минут.\n"
        "\n"
        "Если проблема сохраняется:"
    )


def help_device() -> str:
    return (
        "📱 Проблема с устройством\n"
        "\n"
        "Попробуй:\n"
        "\n"
        "1. Отключить неиспользуемое устройство в боте.\n"
        "2. Добавить текущее заново.\n"
        "3. Получить ссылку и обновить её в Happ.\n"
        "\n"
        "Если не помогло — напиши в поддержку."
    )


def support(settings: Settings) -> str:
    return (
        "💬 Поддержка\n"
        "\n"
        "Если проблема не решилась, напиши нам.\n"
        "\n"
        "Среднее время ответа:\n"
        f"{settings.support_response_time}"
    )


def support_not_configured() -> str:
    return (
        "💬 Поддержка\n"
        "\n"
        "Контакт поддержки ещё не указан.\n"
        "Нужно заполнить SUPPORT_USERNAME в конфигурации."
    )


def generic_error() -> str:
    return (
        "❌ Что-то пошло не так.\n"
        "\n"
        "Попробуй ещё раз."
    )


def subscription_inactive() -> str:
    return (
        "Сейчас VPN недоступен.\n"
        "\n"
        "Продли подписку, чтобы получить ссылку."
    )


def user_blocked() -> str:
    return (
        "🚫 Доступ ограничен.\n"
        "\n"
        "Если это ошибка — напиши в поддержку."
    )
