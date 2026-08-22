from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from app.api.deps import vpn_service_dep
from app.services.vpn_service import VpnService
from app.utils.security import is_valid_subscription_token

router = APIRouter()


@router.get("/s/{token}", response_class=PlainTextResponse)
async def happ_subscription(
    token: str,
    vpn_service: VpnService = Depends(vpn_service_dep),
) -> str:
    if not is_valid_subscription_token(token):
        raise HTTPException(status_code=404, detail="Subscription is not available")

    payload = await vpn_service.get_subscription(token)
    if payload is None:
        raise HTTPException(status_code=404, detail="Subscription is not available")
    return payload
