import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from collectarr_sync.config import get_settings
from collectarr_sync.db import initialize_database
from collectarr_sync.main import app


@pytest_asyncio.fixture(autouse=True)
async def sync_database(tmp_path, monkeypatch) -> AsyncIterator[None]:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SYNC_API_KEY", "test-sync-key")
    monkeypatch.setenv("SYNC_DATABASE_PATH", str(tmp_path / "sync.db"))
    get_settings.cache_clear()
    await initialize_database()
    yield
    get_settings.cache_clear()
    os.environ.pop("SYNC_DATABASE_PATH", None)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def sync_headers() -> dict[str, str]:
    return {"X-Collectarr-Sync-Key": "test-sync-key"}
