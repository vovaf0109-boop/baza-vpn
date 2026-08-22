from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot import texts
from app.bot.callbacks import CB
from app.bot.keyboards.help import help_keyboard, help_topic_keyboard, support_keyboard
from app.bot.navigation import safe_edit
from app.config import Settings

router = Router()


@router.callback_query(F.data == CB.HELP)
async def help_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, texts.help_home(), help_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.HELP_CONNECTION)
async def help_connection(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, texts.help_connection(), help_topic_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.HELP_LINK)
async def help_link(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, texts.help_link(), help_topic_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.HELP_SPEED)
async def help_speed(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, texts.help_speed(), help_topic_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.HELP_DEVICE)
async def help_device(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, texts.help_device(), help_topic_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.HELP_SUPPORT)
async def help_support(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await state.clear()
    text = texts.support(settings) if settings.support_username else texts.support_not_configured()
    await safe_edit(callback, text, support_keyboard(settings))
    await callback.answer()
