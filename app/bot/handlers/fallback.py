from aiogram import Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("Кнопка устарела. Открой меню ещё раз.", show_alert=True)
