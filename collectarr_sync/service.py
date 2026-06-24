import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import aiosqlite

from collectarr_sync.config import get_settings
from collectarr_sync.db import connect
from collectarr_sync.schemas import (
    RejectedChange,
    SyncChangeIn,
    SyncChangeOut,
    SyncChangesResponse,
    SyncDeviceResponse,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncStatusResponse,
    SYNC_PROTOCOL_VERSION,
    SyncedEntity,
    as_utc,
)

logger = logging.getLogger("collectarr_sync.service")


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return as_utc(value).isoformat().replace("+00:00", "Z")


def parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class SyncService:
    _last_pruned_at: datetime | None = None
    _prune_interval = timedelta(days=1)

    @classmethod
    def reset_prune_state_for_testing(cls) -> None:
        cls._last_pruned_at = None

    async def push(
        self, request: SyncPushRequest, *, user_id: str = ""
    ) -> SyncPushResponse:
        server_time = utc_now()
        accepted: list[SyncChangeOut] = []
        rejected: list[RejectedChange] = []

        connection = await connect()
        try:
            for change in request.changes:
                # Idempotency: a retried push carrying the same client_change_id
                # must not append a duplicate change log entry.
                if change.client_change_id is not None:
                    existing = await self._find_change_by_client_id(
                        connection,
                        user_id=user_id,
                        device_id=request.device_id,
                        client_change_id=change.client_change_id,
                    )
                    if existing is not None:
                        accepted.append(self._change_from_row(existing))
                        continue

                current = await self._get_entity(
                    connection, change.entity_type, change.entity_id, user_id=user_id
                )
                current_client_changed_at = (
                    parse_dt(current["client_changed_at"]) if current else None
                )
                if (
                    current_client_changed_at
                    and current_client_changed_at > change.client_changed_at
                ):
                    rejected.append(
                        RejectedChange(
                            entity_type=change.entity_type,
                            entity_id=change.entity_id,
                            reason="server_has_newer_client_change",
                            current_client_changed_at=current_client_changed_at,
                            current_action=current["action"],
                            current_payload=json.loads(current["payload_json"]),
                        )
                    )
                    continue

                accepted_change = await self._accept_change(
                    connection=connection,
                    device_id=request.device_id,
                    change=change,
                    changed_at=server_time,
                    user_id=user_id,
                )
                accepted.append(accepted_change)

            await connection.commit()
            if await self._prune_changes_if_due(connection, server_time):
                await connection.commit()
        finally:
            await connection.close()

        logger.info(
            "sync push: user=%s device=%s accepted=%d rejected=%d",
            user_id or "<api-key>",
            request.device_id,
            len(accepted),
            len(rejected),
        )
        return SyncPushResponse(server_time=server_time, accepted=accepted, rejected=rejected)

    async def pull(
        self, since: datetime | None, *, user_id: str = ""
    ) -> SyncPullResponse:
        server_time = utc_now()
        connection = await connect()
        try:
            if await self._prune_changes_if_due(connection, server_time):
                await connection.commit()
            entities = await self._list_entities(connection, since, user_id=user_id)
            changes = (
                await self._list_changes(connection, since, user_id=user_id)
                if since
                else []
            )
        finally:
            await connection.close()
        return SyncPullResponse(server_time=server_time, entities=entities, changes=changes)

    async def changes(
        self, since: datetime | None, *, user_id: str = ""
    ) -> SyncChangesResponse:
        server_time = utc_now()
        connection = await connect()
        try:
            if await self._prune_changes_if_due(connection, server_time):
                await connection.commit()
            changes = await self._list_changes(connection, since, user_id=user_id)
        finally:
            await connection.close()
        return SyncChangesResponse(server_time=server_time, changes=changes)

    async def status(self, schema_version: int, *, user_id: str = "") -> SyncStatusResponse:
        server_time = utc_now()
        settings = get_settings()
        connection = await connect()
        try:
            entity_count = await self._count(connection, "entities", user_id=user_id)
            tombstone_count = await self._count_tombstones(connection, user_id=user_id)
            change_count = await self._count(connection, "changes", user_id=user_id)
            last_changed_at = await self._last_changed_at(connection, user_id=user_id)
        finally:
            await connection.close()
        return SyncStatusResponse(
            server_time=server_time,
            protocol_version=SYNC_PROTOCOL_VERSION,
            schema_version=schema_version,
            entity_count=entity_count,
            tombstone_count=tombstone_count,
            change_count=change_count,
            retention_days=settings.sync_change_retention_days,
            last_changed_at=last_changed_at,
        )

    async def devices(self, *, user_id: str = "") -> list[SyncDeviceResponse]:
        connection = await connect()
        try:
            cursor = await connection.execute(
                """
                select
                  device_id,
                  count(*) as change_count,
                  min(changed_at) as first_seen_at,
                  max(changed_at) as last_seen_at
                from changes
                where user_id = ?
                group by device_id
                order by max(changed_at) desc, device_id
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()
        finally:
            await connection.close()
        return [
            SyncDeviceResponse(
                device_id=row["device_id"],
                change_count=int(row["change_count"]),
                first_seen_at=parse_dt(row["first_seen_at"]),
                last_seen_at=parse_dt(row["last_seen_at"]),
            )
            for row in rows
            if row["first_seen_at"] and row["last_seen_at"]
        ]

    async def remove_device(self, device_id: str, *, user_id: str = "") -> int:
        connection = await connect()
        try:
            cursor = await connection.execute(
                "delete from changes where user_id = ? and device_id = ?",
                (user_id, device_id),
            )
            removed = cursor.rowcount
            await connection.commit()
        finally:
            await connection.close()
        return removed

    async def _accept_change(
        self,
        connection: aiosqlite.Connection,
        device_id: str,
        change: SyncChangeIn,
        changed_at: datetime,
        *,
        user_id: str = "",
    ) -> SyncChangeOut:
        change_id = str(uuid.uuid4())
        payload_json = json.dumps(change.payload, separators=(",", ":"), sort_keys=True)
        deleted_at = iso(changed_at) if change.action == "delete" else None
        await connection.execute(
            """
            insert into entities (
              entity_type, entity_id, action, payload_json, source_device_id,
              client_changed_at, changed_at, deleted_at, user_id
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(user_id, entity_type, entity_id) do update set
              action = excluded.action,
              payload_json = excluded.payload_json,
              source_device_id = excluded.source_device_id,
              client_changed_at = excluded.client_changed_at,
              changed_at = excluded.changed_at,
              deleted_at = excluded.deleted_at,
              user_id = excluded.user_id
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
                user_id,
            ),
        )
        await connection.execute(
            """
            insert into changes (
              id, entity_type, entity_id, action, payload_json, device_id,
              client_change_id, client_changed_at, changed_at, user_id
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change_id,
                change.entity_type,
                change.entity_id,
                change.action,
                payload_json,
                device_id,
                change.client_change_id,
                iso(change.client_changed_at),
                iso(changed_at),
                user_id,
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

    async def _prune_changes(self, connection: aiosqlite.Connection, server_time: datetime) -> None:
        retention_days = get_settings().sync_change_retention_days
        cutoff = server_time - timedelta(days=retention_days)
        cursor = await connection.execute(
            """
            delete from changes
            where changed_at < ?
            """,
            (iso(cutoff),),
        )
        if cursor.rowcount:
            logger.info("sync prune: removed %d change rows older than %s", cursor.rowcount, iso(cutoff))

    async def _prune_changes_if_due(
        self, connection: aiosqlite.Connection, server_time: datetime
    ) -> bool:
        if (
            self.__class__._last_pruned_at is not None
            and server_time - self.__class__._last_pruned_at < self._prune_interval
        ):
            return False
        await self._prune_changes(connection, server_time)
        self.__class__._last_pruned_at = server_time
        return True

    async def _get_entity(
        self,
        connection: aiosqlite.Connection,
        entity_type: str,
        entity_id: str,
        *,
        user_id: str = "",
    ) -> aiosqlite.Row | None:
        cursor = await connection.execute(
            """
            select * from entities
            where user_id = ? and entity_type = ? and entity_id = ?
            """,
            (user_id, entity_type, entity_id),
        )
        return await cursor.fetchone()

    async def _find_change_by_client_id(
        self,
        connection: aiosqlite.Connection,
        *,
        user_id: str,
        device_id: str,
        client_change_id: str,
    ) -> aiosqlite.Row | None:
        cursor = await connection.execute(
            """
            select * from changes
            where user_id = ? and device_id = ? and client_change_id = ?
            order by seq desc
            limit 1
            """,
            (user_id, device_id, client_change_id),
        )
        return await cursor.fetchone()

    async def _count(self, connection: aiosqlite.Connection, table: str, *, user_id: str = "") -> int:
        if table not in {"entities", "changes"}:
            raise ValueError("Unsupported sync table")
        cursor = await connection.execute(
            f"select count(*) as count from {table} where user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return int(row["count"])

    async def _count_tombstones(self, connection: aiosqlite.Connection, *, user_id: str = "") -> int:
        cursor = await connection.execute(
            """
            select count(*) as count from entities
            where user_id = ? and deleted_at is not null
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return int(row["count"])

    async def _last_changed_at(
        self, connection: aiosqlite.Connection, *, user_id: str = ""
    ) -> datetime | None:
        cursor = await connection.execute(
            """
            select max(changed_at) as changed_at
            from entities
            where user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return parse_dt(row["changed_at"]) if row["changed_at"] else None

    async def _list_entities(
        self,
        connection: aiosqlite.Connection,
        since: datetime | None,
        *,
        user_id: str = "",
    ) -> list[SyncedEntity]:
        if since:
            cursor = await connection.execute(
                """
                select * from entities
                where changed_at > ? and user_id = ?
                order by changed_at, entity_type, entity_id
                """,
                (iso(since), user_id),
            )
        else:
            cursor = await connection.execute(
                """
                select * from entities
                where user_id = ?
                order by changed_at, entity_type, entity_id
                """,
                (user_id,),
            )
        return [self._entity_from_row(row) for row in await cursor.fetchall()]

    async def _list_changes(
        self,
        connection: aiosqlite.Connection,
        since: datetime | None,
        *,
        user_id: str = "",
    ) -> list[SyncChangeOut]:
        if since:
            cursor = await connection.execute(
                """
                select * from changes
                where changed_at > ? and user_id = ?
                order by seq
                """,
                (iso(since), user_id),
            )
        else:
            cursor = await connection.execute(
                """
                select * from changes
                where user_id = ?
                order by seq
                """,
                (user_id,),
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
