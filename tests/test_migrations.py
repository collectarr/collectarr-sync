import aiosqlite
import pytest

from collectarr_sync.db import CURRENT_SCHEMA_VERSION, initialize_database
from collectarr_sync.config import get_settings


@pytest.mark.asyncio
async def test_fresh_database_applies_schema_version():
    await initialize_database()

    async with aiosqlite.connect(get_settings().sync_database_path) as connection:
        cursor = await connection.execute("select max(version) from schema_migrations")
        row = await cursor.fetchone()

    assert row[0] == CURRENT_SCHEMA_VERSION
