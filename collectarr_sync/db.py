from pathlib import Path

import aiosqlite

from collectarr_sync.config import get_settings

# The v1 database is created as a fresh baseline. There is no database upgrade path.
CURRENT_SCHEMA_VERSION = 1


async def connect() -> aiosqlite.Connection:
    settings = get_settings()
    db_path = Path(settings.sync_database_path)
    is_memory = str(db_path) == ":memory:"
    if not is_memory:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(db_path)
    connection.row_factory = aiosqlite.Row
    await connection.execute("pragma foreign_keys = on")
    # WAL + a busy timeout keep concurrent multi-device pushes from failing with
    # "database is locked" under SQLite. WAL is unavailable for in-memory DBs.
    if not is_memory:
        await connection.execute("pragma journal_mode = wal")
    await connection.execute("pragma busy_timeout = 5000")
    return connection


async def initialize_database() -> None:
    connection = await connect()
    try:
        await connection.executescript(
            """
            create table if not exists entities (
              user_id text not null default '',
              entity_type text not null,
              entity_id text not null,
              action text not null check (action in ('upsert', 'delete')),
              payload_json text not null,
              source_device_id text not null,
              client_changed_at text not null,
              changed_at text not null,
              deleted_at text,
              primary key (user_id, entity_type, entity_id)
            );

            create table if not exists changes (
              seq integer primary key autoincrement,
              id text not null unique,
              user_id text not null default '',
              entity_type text not null,
              entity_id text not null,
              action text not null check (action in ('upsert', 'delete')),
              payload_json text not null,
              device_id text not null,
              client_change_id text,
              client_changed_at text not null,
              changed_at text not null
            );

            create index if not exists ix_changes_changed_at
              on changes (user_id, changed_at);
            create index if not exists ix_changes_entity
              on changes (user_id, entity_type, entity_id);
            create index if not exists ix_changes_user on changes (user_id);
            create unique index if not exists ux_changes_client_change_id
              on changes (user_id, device_id, client_change_id)
              where client_change_id is not null;

            create index if not exists ix_entities_changed_at
              on entities (user_id, changed_at);
            create index if not exists ix_entities_user on entities (user_id);
            """
        )
        await connection.commit()
    finally:
        await connection.close()
