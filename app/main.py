import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import api_router
from app.bot.factory import create_bot, create_dispatcher
from app.config import Settings, get_settings
from app.database import dispose_db, get_session_factory, init_db
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


async def ensure_redis_available(settings: Settings) -> None:
    if not settings.redis_url:
        return

    try:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.redis_url)
        try:
            await redis.ping()
        finally:
            await redis.aclose()
    except Exception:
        if settings.is_production:
            raise RuntimeError("Redis is required but unavailable in production") from None
        logger.warning("redis_unavailable_startup_check_failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings)
    init_db(settings)
    await ensure_redis_available(settings)

    bot = None
    dispatcher = None
    polling_task = None

    if settings.bot_token:
        bot = create_bot(settings)
        dispatcher = create_dispatcher(settings, get_session_factory())
        polling_task = asyncio.create_task(dispatcher.start_polling(bot))
        logger.info("bot_polling_started")
    else:
        logger.warning("bot_token_missing_polling_disabled")

    app.state.settings = settings
    app.state.bot = bot

    yield

    if polling_task is not None:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    if dispatcher is not None:
        await dispatcher.storage.close()
    if bot is not None:
        await bot.session.close()
    await dispose_db()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Baza VPN",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    if settings.allowed_hosts_list and "*" not in settings.allowed_hosts_list:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=list(settings.allowed_hosts_list),
        )

    @app.middleware("http")
    async def add_security_headers(request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    app.include_router(api_router)
    return app


app = create_app()
