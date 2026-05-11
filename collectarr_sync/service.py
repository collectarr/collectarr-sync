import json
import uuid
from datetime import UTC, datetime

import aiosqlite

from collectarr_sync.db import connect
from collectarr_sync.schemas import (
    RejectedChange,
    SyncChangeIn,
    SyncChangeOut,
    SyncChangesResponse,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncedEntity,
    as_utc,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return as_utc(value).isoformat().replace("+00:00", "Z")


def parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class SyncService:
    async def push(self, request: SyncPushRequest) -> SyncPushResponse:
        server_time = utc_now()
        accepted: list[SyncChangeOut] = []
        rejected: list[RejectedChange] = []

        connection = await connect()
        try:
            for change in request.changes:
                current = await self._get_entity(connection, change.entity_type, change.entity_id)
                current_client_changed_at = parse_dt(current["client_changed_at"]) if current else None
                if current_client_changed_at and current_client_changed_at > change.client_changed_at:
                    rejected.append(
                        RejectedChange(
                            entity_type=change.entity_type,
                            entity_id=change.entity_id,
                            reason="server_has_newer_client_change",
                            current_client_changed_at=current_client_changed_at,
                        )
                    )
                    continue

                accepted_change = await self._accept_change(
                    connection=connection,
                    device_id=request.device_id,
                    change=change,
                    changed_at=server_time,
                )
                accepted.append(accepted_change)

            await connection.commit()
        finally:
            await connection.close()

        return SyncPushResponse(server_time=server_time, accepted=accepted, rejected=rejected)

    async def pull(self, since: datetime | None) -> SyncPullResponse:
        server_time = utc_now()
        connection = await connect()
        try:
            entities = await self._list_entities(connection, since)
            changes = await self._list_changes(connection, since)
        finally:
            await connection.close()
        return SyncPullResponse(server_time=server_time, entities=entities, changes=changes)

    async def changes(self, since: datetime | None) -> SyncChangesResponse:
        server_time = utc_now()
        connection = await connect()
        try:
            changes = await self._list_changes(connection, since)
        finally:
            await connection.close()
        return SyncChangesResponse(server_time=server_time, changes=changes)

    async def _accept_change(
        self,
        connection: aiosqlite.Connection,
        device_id: str,
        change: SyncChangeIn,
        changed_at: datetime,
    ) -> SyncChangeOut:
        change_id = str(uuid.uuid4())
        payload_json = json.dumps(change.payload, separators=(",", ":"), sort_keys=True)
        deleted_at = iso(changed_at) if change.action == "delete" else None
        await connection.execute(
            """
            insert into entities (
              entity_type, entity_id, action, payload_json, source_device_id,
              client_changed_at, changed_at, deleted_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(entity_type, entity_id) do update set
              action = excluded.action,
              payload_json = excluded.payload_json,
              source_device_id = excluded.source_device_id,
              client_changed_at = excluded.client_changed_at,
              changed_at = excluded.changed_at,
              deleted_at = excluded.deleted_at
            """,
            (
                change.entity_type,
                change.entity_id,
                change.action,
                payload_json,
                device_id,
                iso(change.client_changed_at),
                iso(changed_at),
                deleted_at,
            ),
        )
        await connection.execute(
            """
            insert into changes (
              id, entity_type, entity_id, action, payload_json, device_id,
              client_changed_at, changed_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change_id,
                change.entity_type,
                change.entity_id,
                change.action,
                payload_json,
                device_id,
                iso(change.client_changed_at),
                iso(changed_at),
            ),
        )
        return SyncChangeOut(
            id=change_id,
            entity_type=change.entity_type,
            entity_id=change.entity_id,
            action=change.action,
            device_id=device_id,
            client_changed_at=change.client_changed_at,
            changed_at=changed_at,
            payload=change.payload,
        )

    async def _get_entity(
        self, connection: aiosqlite.Connection, entity_type: str, entity_id: str
    ) -> aiosqlite.Row | None:
        cursor = await connection.execute(
            """
            select * from entities
            where entity_type = ? and entity_id = ?
            """,
            (entity_type, entity_id),
        )
        return await cursor.fetchone()

    async def _list_entities(
        self, connection: aiosqlite.Connection, since: datetime | None
    ) -> list[SyncedEntity]:
        if since:
            cursor = await connection.execute(
                """
                select * from entities
                where changed_at > ?
                order by changed_at, entity_type, entity_id
                """,
                (iso(since),),
            )
        else:
            cursor = await connection.execute(
                """
                select * from entities
                order by changed_at, entity_type, entity_id
                """
            )
        return [self._entity_from_row(row) for row in await cursor.fetchall()]

    async def _list_changes(
        self, connection: aiosqlite.Connection, since: datetime | None
    ) -> list[SyncChangeOut]:
        if since:
            cursor = await connection.execute(
                """
                select * from changes
                where changed_at > ?
                order by changed_at, id
                """,
                (iso(since),),
            )
        else:
            cursor = await connection.execute(
                """
                select * from changes
                order by changed_at, id
                """
            )
        return [self._change_from_row(row) for row in await cursor.fetchall()]

    def _entity_from_row(self, row: aiosqlite.Row) -> SyncedEntity:
        return SyncedEntity(
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            action=row["action"],
            source_device_id=row["source_device_id"],
            client_changed_at=parse_dt(row["client_changed_at"]),
            changed_at=parse_dt(row["changed_at"]),
            deleted_at=parse_dt(row["deleted_at"]),
            payload=json.loads(row["payload_json"]),
        )

    def _change_from_row(self, row: aiosqlite.Row) -> SyncChangeOut:
        return SyncChangeOut(
            id=row["id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            action=row["action"],
            device_id=row["device_id"],
            client_changed_at=parse_dt(row["client_changed_at"]),
            changed_at=parse_dt(row["changed_at"]),
            payload=json.loads(row["payload_json"]),
        )
