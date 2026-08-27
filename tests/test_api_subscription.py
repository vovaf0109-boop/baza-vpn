import pytest
from fastapi import HTTPException

from app.api.routes.subscription import happ_subscription
from app.services.vpn_providers import VpnProviderConfigurationError


class SpyVpnService:
    def __init__(self, *, raises_configuration_error: bool = False) -> None:
        self.called = False
        self.raises_configuration_error = raises_configuration_error

    async def get_subscription(self, token: str) -> str | None:
        self.called = True
        if self.raises_configuration_error:
            raise VpnProviderConfigurationError("private internal configuration detail")
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


@pytest.mark.asyncio
async def test_provider_configuration_error_returns_safe_response() -> None:
    service = SpyVpnService(raises_configuration_error=True)

    with pytest.raises(HTTPException) as exc:
        await happ_subscription("A" * 40, service)  # type: ignore[arg-type]

    assert exc.value.status_code == 503
    assert exc.value.detail == "Subscription is temporarily unavailable"
    assert service.called is True
