from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.handlers import admin, connect, devices, help, menu, profile, start, subscription


def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(menu.router)
    router.include_router(connect.router)
    router.include_router(subscription.router)
    router.include_router(devices.router)
    router.include_router(help.router)
    router.include_router(profile.router)
    router.include_router(admin.router)

    @router.callback_query()
    async def unknown_callback(callback: CallbackQuery) -> None:
        await callback.answer("Кнопка устарела. Открой меню ещё раз.", show_alert=True)

    return router
