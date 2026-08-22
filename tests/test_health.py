import pytest
from fastapi import HTTPException

from app.api.routes.health import ready


class HealthySession:
    async def execute(self, statement: object) -> object:
        return object()


class BrokenSession:
    async def execute(self, statement: object) -> object:
        raise RuntimeError("db down")


@pytest.mark.asyncio
async def test_ready_returns_ready_when_db_query_succeeds() -> None:
    assert await ready(HealthySession()) == {"status": "ready"}  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_ready_returns_503_when_db_query_fails() -> None:
    with pytest.raises(HTTPException) as exc:
        await ready(BrokenSession())  # type: ignore[arg-type]

    assert exc.value.status_code == 503
