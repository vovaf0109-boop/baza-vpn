from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.models.base import Base

engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or get_settings()
    kwargs = {
        "pool_pre_ping": True,
        "hide_parameters": True,
    }
    if settings.database_url.startswith("postgresql+asyncpg://"):
        kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_recycle": settings.database_pool_recycle_seconds,
                "connect_args": {
                    "command_timeout": settings.database_command_timeout_seconds,
                },
            }
        )
    return create_async_engine(settings.database_url, **kwargs)


def create_session_factory(bind: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind, expire_on_commit=False, autoflush=False)


def init_db(settings: Settings | None = None) -> None:
    global engine, session_factory
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)


async def dispose_db() -> None:
    global engine, session_factory
    if engine is not None:
        await engine.dispose()
    engine = None
    session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if session_factory is None:
        raise RuntimeError("Database is not initialized")
    return session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "Base",
    "create_engine",
    "create_session_factory",
    "dispose_db",
    "engine",
    "get_session",
    "get_session_factory",
    "init_db",
    "session_factory",
]
