import sqlite3

import pytest
from pydantic import ValidationError

from collectarr_sync.config import get_settings
from collectarr_sync.db import initialize_database
from collectarr_sync.schemas import CatalogItemRefPayload


def test_music_and_comics_references_are_supported():
    assert CatalogItemRefPayload(kind="music", id="album").kind == "music"
    assert CatalogItemRefPayload(kind="comic", id="issue").kind == "comic"
    for kind in ("anime", "boardgame", "book", "game", "manga", "movie", "tv"):
        with pytest.raises(ValidationError):
            CatalogItemRefPayload(kind=kind, id="item")


@pytest.mark.asyncio
async def test_versioned_initialization_preserves_existing_rows():
    path = get_settings().sync_database_path
    with sqlite3.connect(path) as db:
        assert db.execute("pragma user_version").fetchone()[0] == 1
        db.execute("insert into collection_shares values (?, ?, ?, ?, ?)",
                   ("user", "collection", "token", "private", '{}'))
    await initialize_database()
    with sqlite3.connect(path) as db:
        assert db.execute("select token from collection_shares").fetchone()[0] == "token"


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [0, 2])
async def test_unknown_existing_database_is_left_intact(tmp_path, monkeypatch, version):
    path = tmp_path / "existing.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("create table preserved (value text)")
        db.execute("insert into preserved values ('personal data')")
        db.execute(f"pragma user_version = {version}")
    monkeypatch.setenv("SYNC_DATABASE_PATH", str(path))
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="left untouched"):
        await initialize_database()
    with sqlite3.connect(path) as db:
        assert db.execute("pragma user_version").fetchone()[0] == version
        assert db.execute("select value from preserved").fetchone()[0] == "personal data"
        assert db.execute("select name from sqlite_master where type = 'table'").fetchall() == [("preserved",)]
