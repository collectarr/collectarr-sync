from pathlib import Path

import aiosqlite

from collectarr_sync.config import get_settings

# The current schema is baseline 1. Future changes require ordered migrations.
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
        row = await (await connection.execute("pragma user_version")).fetchone()
        version = row[0]
        rows = await (await connection.execute(
            "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
        )).fetchall()
        tables = {row[0] for row in rows}
        if version == CURRENT_SCHEMA_VERSION:
            if tables != {"entities", "changes", "collection_shares"}:
                raise RuntimeError("Versioned Sync database differs from the released schema.")
            return
        if version != 0 or tables:
            raise RuntimeError("Existing database left untouched; no explicit migration is registered.")
        await connection.executescript(
            """
            begin immediate;
            create table entities (
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
            create table if not exists collection_shares (
              user_id text not null,
              collection_id text not null,
              token text unique,
              visibility text not null check (visibility in ('private', 'partial', 'public')),
              payload_json text not null,
              primary key (user_id, collection_id)
            );
            pragma user_version = 1;
            commit;
            """
        )
        await connection.commit()
    finally:
        await connection.close()
