import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import UserStatus
from app.services.user_service import UserService
from app.utils.datetime import utcnow


@pytest.mark.asyncio
async def test_user_creation(user_service: UserService) -> None:
    user = await user_service.create(
        telegram_id=1001,
        username="anna",
        first_name="Анна",
    )
    assert user.id is not None
    assert user.telegram_id == 1001
    assert user.username == "anna"
    assert user.status == UserStatus.ACTIVE
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_duplicate_telegram_user(user_service: UserService) -> None:
    first = await user_service.create(
        telegram_id=1002,
        username="one",
        first_name="One",
    )
    second = await user_service.create(
        telegram_id=1002,
        username="two",
        first_name="Two",
    )
    assert first.id == second.id
    found = await user_service.get_by_telegram_id(1002)
    assert found is not None
    assert found.id == first.id
    assert found.username == "two"
    assert found.first_name == "Two"


@pytest.mark.asyncio
async def test_user_updated_at_changes_on_profile_update(
    user_service: UserService,
    session: AsyncSession,
) -> None:
    user = await user_service.create(
        telegram_id=1003,
        username="before",
        first_name="Before",
    )
    user.updated_at = utcnow().replace(year=2020)
    await session.flush()

    old_updated_at = user.updated_at
    await user_service.update_profile(
        user,
        username="after",
        first_name="After",
    )
    await session.refresh(user)

    assert user.username == "after"
    assert user.first_name == "After"
    assert user.updated_at != old_updated_at
