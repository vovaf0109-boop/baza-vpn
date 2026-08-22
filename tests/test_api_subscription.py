import pytest
from fastapi import HTTPException

from app.api.routes.subscription import happ_subscription


class SpyVpnService:
    def __init__(self) -> None:
        self.called = False

    async def get_subscription(self, token: str) -> str | None:
        self.called = True
        return None


@pytest.mark.asyncio
async def test_malformed_subscription_token_is_rejected_before_db_lookup() -> None:
    service = SpyVpnService()

    with pytest.raises(HTTPException) as exc:
        await happ_subscription("../bad", service)  # type: ignore[arg-type]

    assert exc.value.status_code == 404
    assert service.called is False


@pytest.mark.asyncio
async def test_missing_subscription_token_returns_not_found() -> None:
    service = SpyVpnService()

    with pytest.raises(HTTPException) as exc:
        await happ_subscription("A" * 40, service)  # type: ignore[arg-type]

    assert exc.value.status_code == 404
    assert service.called is True
