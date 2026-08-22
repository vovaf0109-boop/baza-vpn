from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.config import Settings
from app.services.admin_service import AdminService
from app.utils.datetime import format_date_ru
from app.utils.html import html_escape

router = Router()


def _is_admin(message: Message, settings: Settings) -> bool:
    return bool(message.from_user and settings.is_admin(message.from_user.id))


@router.message(Command("admin"))
async def admin_help(message: Message, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await message.answer(
        "🛠 Админ\n"
        "\n"
        "/user &lt;id&gt; — пользователь\n"
        "/block &lt;id&gt; — заблокировать\n"
        "/unblock &lt;id&gt; — разблокировать\n"
        "/extend &lt;id&gt; &lt;дни&gt; — продлить подписку\n"
        "/payments &lt;id&gt; — платежи\n"
        "/servers — VPN-серверы"
    )


@router.message(Command("user"))
async def admin_user(
    message: Message,
    command: CommandObject,
    settings: Settings,
    admin_service: AdminService,
) -> None:
    if not _is_admin(message, settings):
        return
    if not command.args:
        await message.answer("Использование: /user &lt;id&gt;")
        return

    user = await admin_service.find_user(command.args)
    if user is None:
        await message.answer("Пользователь не найден.")
        return

    data = await admin_service.user_overview(user)
    subscription = data["subscription"]
    devices = data["devices"]
    if subscription is None:
        sub_line = "подписка: нет"
    else:
        sub_line = (
            f"подписка: {html_escape(subscription.status)}\n"
            f"до: {format_date_ru(subscription.expires_at)}"
        )

    await message.answer(
        f"👤 #{user.id}\n"
        f"telegram: {user.telegram_id}\n"
        f"username: {html_escape(user.username or '—')}\n"
        f"статус: {html_escape(user.status)}\n"
        f"{sub_line}\n"
        f"устройства: {len(devices)}"
    )


@router.message(Command("block"))
async def admin_block(
    message: Message,
    command: CommandObject,
    settings: Settings,
    admin_service: AdminService,
) -> None:
    if not _is_admin(message, settings):
        return
    if not command.args:
        await message.answer("Использование: /block &lt;id&gt;")
        return
    user = await admin_service.find_user(command.args)
    if user is None:
        await message.answer("Пользователь не найден.")
        return
    await admin_service.block_user(user)
    await message.answer(f"Пользователь #{user.id} заблокирован.")


@router.message(Command("unblock"))
async def admin_unblock(
    message: Message,
    command: CommandObject,
    settings: Settings,
    admin_service: AdminService,
) -> None:
    if not _is_admin(message, settings):
        return
    if not command.args:
        await message.answer("Использование: /unblock &lt;id&gt;")
        return
    user = await admin_service.find_user(command.args)
    if user is None:
        await message.answer("Пользователь не найден.")
        return
    await admin_service.unblock_user(user)
    await message.answer(f"Пользователь #{user.id} разблокирован.")


@router.message(Command("extend"))
async def admin_extend(
    message: Message,
    command: CommandObject,
    settings: Settings,
    admin_service: AdminService,
) -> None:
    if not _is_admin(message, settings):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /extend &lt;id&gt; &lt;дни&gt;")
        return
    days = int(parts[1])
    if days <= 0 or days > settings.admin_max_extend_days:
        await message.answer(
            f"Количество дней должно быть от 1 до {settings.admin_max_extend_days}."
        )
        return
    user = await admin_service.find_user(parts[0])
    if user is None:
        await message.answer("Пользователь не найден.")
        return
    subscription = await admin_service.extend_subscription(user, days)
    await message.answer(
        f"Подписка #{user.id} продлена до {format_date_ru(subscription.expires_at)}."
    )


@router.message(Command("payments"))
async def admin_payments(
    message: Message,
    command: CommandObject,
    settings: Settings,
    admin_service: AdminService,
) -> None:
    if not _is_admin(message, settings):
        return
    if not command.args:
        await message.answer("Использование: /payments &lt;id&gt;")
        return
    user = await admin_service.find_user(command.args)
    if user is None:
        await message.answer("Пользователь не найден.")
        return
    payments = await admin_service.list_payments(user)
    if not payments:
        await message.answer("Платежей нет.")
        return
    lines = [
        (
            f"#{item.id} {html_escape(item.status)} {item.amount} "
            f"{html_escape(item.currency)} ({html_escape(item.provider)})"
        )
        for item in payments
    ]
    await message.answer("Платежи:\n" + "\n".join(lines))


@router.message(Command("servers"))
async def admin_servers(
    message: Message,
    settings: Settings,
    admin_service: AdminService,
) -> None:
    if not _is_admin(message, settings):
        return
    servers = await admin_service.list_servers()
    if not servers:
        await message.answer("Серверы ещё не добавлены.")
        return
    lines = [
        (
            f"#{item.id} {html_escape(item.country)} — {html_escape(item.name)} "
            f"[{html_escape(item.status)}] load={item.load}"
        )
        for item in servers
    ]
    await message.answer("Серверы:\n" + "\n".join(lines))
