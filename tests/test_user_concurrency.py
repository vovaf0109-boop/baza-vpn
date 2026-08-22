import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, User
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_concurrent_user_create_keeps_telegram_id_unique(tmp_path) -> None:
    db_path = tmp_path / "concurrency.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_user(username: str) -> int:
        async with factory() as session:
            user = await UserService(session).create(
                telegram_id=9001,
                username=username,
                first_name=username.title(),
            )
            await session.commit()
            return user.id

    ids = await asyncio.gather(create_user("first"), create_user("second"))

    async with factory() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(User.telegram_id == 9001)
        )
        count = int(result.scalar_one())

    await engine.dispose()

    assert count == 1
    assert ids[0] == ids[1]
