from pathlib import Path

import aiosqlite

from collectarr_sync.config import get_settings

# Single clean schema baseline. The sync store is reset to schema version 1:
# no historical upgrade path is carried because the service is deployed fresh.
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
    """Create the full sync schema.

    Personal state is partitioned by ``user_id`` so a single hosted instance can
    safely serve multiple users without one user overwriting another's rows.
    Legacy API-key auth maps to the empty ``user_id`` partition (single-user).
    """
    await connection.executescript(
        """
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

        create table changes (
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

        create index ix_changes_changed_at on changes (user_id, changed_at);
        create index ix_changes_entity on changes (user_id, entity_type, entity_id);
        create index ix_changes_user on changes (user_id);
        create unique index ux_changes_client_change_id
          on changes (user_id, device_id, client_change_id)
          where client_change_id is not null;

        create index ix_entities_changed_at on entities (user_id, changed_at);
        create index ix_entities_user on entities (user_id);

        insert into schema_migrations (version) values (1);
        """
    )
