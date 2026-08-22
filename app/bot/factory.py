import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.bot.handlers import setup_routers
from app.bot.keyboards.main import error_keyboard
from app.bot.middlewares.db import DatabaseMiddleware
from app.bot.texts import generic_error
from app.config import Settings

logger = logging.getLogger(__name__)


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> Dispatcher:
    storage = MemoryStorage()
    if settings.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            storage = RedisStorage.from_url(settings.redis_url)
        except Exception:
            if settings.is_production:
                raise
            logger.warning("redis_unavailable_using_memory_storage")

    dp = Dispatcher(storage=storage)
    dp.update.middleware(DatabaseMiddleware(session_factory, settings))
    dp.include_router(setup_routers())

    @dp.errors()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("unhandled_error %s", event.exception)
        update = event.update
        target = None
        if update.message:
            target = update.message
        elif update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.answer("Ошибка. Попробуй ещё раз.", show_alert=True)
            except Exception:
                logger.exception("failed_to_answer_error_callback")
            target = update.callback_query.message
        if target is not None:
            try:
                await target.answer(
                    generic_error(),
                    reply_markup=error_keyboard(settings),
                )
            except Exception:
                logger.exception("failed_to_send_error_message")

    return dp
