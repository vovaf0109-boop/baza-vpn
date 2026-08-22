import pytest

from app.exceptions import DeviceLimitReachedError, UserBlockedError
from app.services.device_service import DeviceService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_device_limit(
    user_service: UserService,
    device_service: DeviceService,
) -> None:
    user = await user_service.create(telegram_id=3001, username="dev", first_name="Dev")
    await device_service.add(user, "iPhone")
    await device_service.add(user, "MacBook")
    await device_service.add(user, "iPad")

    assert await device_service.count_active(user) == 3
    with pytest.raises(DeviceLimitReachedError) as exc:
        await device_service.add(user, "Windows")
    assert exc.value.current == 3
    assert exc.value.limit == 3


@pytest.mark.asyncio
async def test_device_revoke_frees_slot(
    user_service: UserService,
    device_service: DeviceService,
) -> None:
    user = await user_service.create(telegram_id=3002, username="rev", first_name="Rev")
    first = await device_service.add(user, "iPhone")
    await device_service.add(user, "MacBook")
    await device_service.add(user, "iPad")
    await device_service.revoke(user, first.id)
    added = await device_service.add(user, "Новый телефон")
    assert added.name == "Новый телефон"
    assert await device_service.count_active(user) == 3


@pytest.mark.asyncio
async def test_blocked_user_cannot_add_device(
    user_service: UserService,
    device_service: DeviceService,
) -> None:
    user = await user_service.create(telegram_id=3003, username="blocked", first_name="Blocked")
    await user_service.block(user)

    with pytest.raises(UserBlockedError):
        await device_service.add(user, "iPhone")
