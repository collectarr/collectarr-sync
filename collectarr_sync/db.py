from pathlib import Path

import aiosqlite

from collectarr_sync.config import get_settings

CURRENT_SCHEMA_VERSION = 1


async def connect() -> aiosqlite.Connection:
    settings = get_settings()
    db_path = Path(settings.sync_database_path)
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(db_path)
    connection.row_factory = aiosqlite.Row
    await connection.execute("pragma foreign_keys = on")
    return connection


async def initialize_database() -> None:
    connection = await connect()
    try:
        await _ensure_migration_table(connection)
        current_version = await _current_version(connection)
        if current_version < 1:
            await _migrate_to_v1(connection)
        await connection.commit()
    finally:
        await connection.close()


async def _ensure_migration_table(connection: aiosqlite.Connection) -> None:
    await connection.execute(
        """
        create table if not exists schema_migrations (
          version integer primary key,
          applied_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )


async def _current_version(connection: aiosqlite.Connection) -> int:
    cursor = await connection.execute("select coalesce(max(version), 0) from schema_migrations")
    row = await cursor.fetchone()
    return int(row[0])


async def _migrate_to_v1(connection: aiosqlite.Connection) -> None:
    await connection.executescript(
        """
        create table entities (
          entity_type text not null,
          entity_id text not null,
          action text not null check (action in ('upsert', 'delete')),
          payload_json text not null,
          source_device_id text not null,
          client_changed_at text not null,
          changed_at text not null,
          deleted_at text,
          primary key (entity_type, entity_id)
        );

        create table changes (
          id text primary key,
          entity_type text not null,
          entity_id text not null,
          action text not null check (action in ('upsert', 'delete')),
          payload_json text not null,
          device_id text not null,
          client_changed_at text not null,
          changed_at text not null
        );

        create index ix_changes_changed_at on changes (changed_at);
        create index ix_changes_entity on changes (entity_type, entity_id);
        create index ix_entities_changed_at on entities (changed_at);

        insert into schema_migrations (version) values (1);
        """
    )
