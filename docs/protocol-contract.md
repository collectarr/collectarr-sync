# Sync Protocol Contract v1

## Overview

The Collectarr Sync protocol enables multi-device personal library
synchronization. It is designed for user-hosted deployments where a single
sync service serves one user's devices.

## Protocol Version

The current protocol version is **1**. Clients should check the
`protocol_version` field in `/health` or `/sync/status` before syncing.

```
GET /health
→ { "status": "ok", "protocol_version": 1, "schema_version": 3 }
```

## Authentication

All `/sync/*` endpoints require the `X-Collectarr-Sync-Key` header matching
the server's `SYNC_API_KEY`. Invalid keys return `401 Unauthorized`.

## Endpoints

### `GET /health`

System health check. No authentication required.

Response:
```json
{
  "status": "ok",
  "protocol_version": 1,
  "schema_version": 3
}
```

### `GET /sync/status`

Returns sync service statistics.

Response (`SyncStatusResponse`):
```json
{
  "server_time": "2026-01-15T10:00:00Z",
  "protocol_version": 1,
  "schema_version": 3,
  "entity_count": 42,
  "tombstone_count": 3,
  "change_count": 150,
  "retention_days": 90,
  "last_changed_at": "2026-01-15T09:55:00Z"
}
```

### `GET /sync/devices`

Returns known devices with change counts and timestamps.

Response: `list[SyncDeviceResponse]`
```json
[
  {
    "device_id": "desktop-abc123",
    "change_count": 85,
    "first_seen_at": "2026-01-01T00:00:00Z",
    "last_seen_at": "2026-01-15T09:55:00Z"
  }
]
```

### `POST /sync/push`

Push local changes to the service. Changes are processed in order.

Request (`SyncPushRequest`):
```json
{
  "device_id": "desktop-abc123",
  "changes": [
    {
      "entity_type": "owned_item",
      "entity_id": "owned-1",
      "action": "upsert",
      "client_changed_at": "2026-01-15T10:00:00Z",
      "payload": {
        "item_id": "comic-1",
        "condition": "Near Mint",
        "grade": "9.8"
      }
    }
  ]
}
```

Response (`SyncPushResponse`):
```json
{
  "server_time": "2026-01-15T10:00:01Z",
  "accepted": [
    {
      "id": "change-uuid",
      "entity_type": "owned_item",
      "entity_id": "owned-1",
      "action": "upsert",
      "device_id": "desktop-abc123",
      "client_changed_at": "2026-01-15T10:00:00Z",
      "changed_at": "2026-01-15T10:00:01Z",
      "payload": { "..." : "..." }
    }
  ],
  "rejected": [
    {
      "entity_type": "owned_item",
      "entity_id": "owned-2",
      "reason": "server_has_newer_client_change",
      "current_client_changed_at": "2026-01-15T10:01:00Z",
      "current_action": "upsert",
      "current_payload": { "..." : "..." }
    }
  ]
}
```

### `POST /sync/pull`

Pull entities and changes from the service.

Request (`SyncPullRequest`):
```json
{
  "since": "2026-01-15T00:00:00Z"
}
```

- `since = null`: full snapshot (all entities, no changes)
- `since` set: entities changed after that time + change log entries

Response (`SyncPullResponse`):
```json
{
  "server_time": "2026-01-15T10:00:01Z",
  "entities": [
    {
      "entity_type": "owned_item",
      "entity_id": "owned-1",
      "action": "upsert",
      "source_device_id": "desktop-abc123",
      "client_changed_at": "2026-01-15T10:00:00Z",
      "changed_at": "2026-01-15T10:00:01Z",
      "deleted_at": null,
      "payload": { "..." : "..." }
    }
  ],
  "changes": []
}
```

### `GET /sync/changes?since=...`

Lightweight change log without full entity snapshots.

## Entity Types

| Type | Description |
|------|-------------|
| `owned_item` | User's owned collection entry |
| `tracking_entry` | User tracking state for owned or tracked-only items |
| `wishlist_item` | Wishlist entry |
| `library_item_snapshot` | Catalog metadata snapshot |
| `note` | Personal notes on items |

## Conflict Resolution

Policy: **last-write-wins by `client_changed_at`**.

When a push contains a change with `client_changed_at` older than the
server's existing `client_changed_at` for the same entity, the change is
rejected. The rejection includes the server's current state so the client
can show a diff.

Client actions on rejection:
- **Keep service**: Accept the server version (default)
- **Retry local**: Queue a new push with an updated `client_changed_at`
- **Dismiss**: Discard the conflict notification

## Tombstones

Deletes are stored with `action = "delete"` and a non-null `deleted_at`.
Tombstones persist until the entity is overwritten by a new upsert.

## Change Retention

The change log is pruned after `SYNC_CHANGE_RETENTION_DAYS` (default 90).
Clients that haven't synced within the retention window should do a full
pull (`since = null`) to get the complete entity snapshot.

## Backwards Compatibility

- New optional fields may be added to payloads without incrementing the
  protocol version.
- Breaking changes (removed fields, changed semantics) increment
  `protocol_version`.
- Clients should check `protocol_version` on `/health` and warn users if
  the server version is newer than supported.
