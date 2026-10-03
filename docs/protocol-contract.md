# Sync Protocol Contract v1

## Ownership and identity

Collectarr Sync mirrors complete App-owned library entries and personal state
between devices for one authenticated user. Core remains the source-neutral
catalog service. Sync does not perform provider search or ingest.

Every change is scoped by authenticated user, `entity_type`, and `entity_id`.
For `library_entry`, `entity_id` is the entry's stable local identity. Its
payload contains the entry's catalog fields, personal fields, optional Core
provenance, and record timestamps. `source_catalog_ref` is provenance only; it
does not make the entry a child of a Core record. `catalog_data` is the
entry-owned snapshot and remains editable independently on each entry.

## Version and reset

The wire protocol and SQLite store schema are version 1. A fresh v1 deployment
is required. Older personal payload formats are unsupported after the
coordinated cutover. Do not point the new protocol at a live old-format Sync
database or delete the old database as part of implementation.

```http
GET /health
```

```json
{ "status": "ok", "protocol_version": 1, "schema_version": 1 }
```

## Authentication and endpoints

Sync partitions entities and changes by the authenticated user. A user's
devices can only read, overwrite, or delete rows in that user's partition.
Deployments must configure per-user authentication; the shared development key
is only suitable for a single-user local instance.

- `POST /sync/push` accepts personal changes.
- `POST /sync/pull` returns current entities, optionally since a timestamp.
- `GET /sync/changes?since=...` returns the ordered change log.
- `GET /sync/status` returns counts for the authenticated user.

Each pushed change has `entity_type`, `entity_id`, `action` (`upsert` or
`delete`), `client_changed_at`, and a typed payload. Deletes use tombstones and
may send an empty payload when the entity type permits it.

## Supported personal entities

| Entity type | Payload |
|---|---|
| `library_entry` | `kind`, `catalog_data`, `personal_data`, optional `source_catalog_ref`, `updated_at`, and optional `created_at`/`deleted_at`. `id` may be included and must match `entity_id`. Kind-specific data stays opaque to Sync. A personal `quantity` value is retained. |
| `wishlist_item` | Catalog Item reference, target price, currency, notes, and creation time. |
| `tracking_entry` | Required local `library_entry_ref`, status, dates, progress, and kind-owned progress fields. |
| `tracking_unit` | Required local `library_entry_ref`, optional tracking entry ID, completion time, and kind-owned unit coordinates. |
| `watch_session` | Required local `library_entry_ref`, watch time, source, rating, notes, and kind-owned episode coordinates. |
| `music_listen_event` | Required Music `library_entry_ref`, listen timestamp, and personal location or notes. |
| `custom_episode` | Local `library_entry_ref` for an Anime or TV entry and custom episode fields. |
| `metadata_override` | Local `library_entry_ref`, field key, and override value. |
| `location` | User-owned location name, parent, description, and order. |
| `user_folder` | User-owned folder name, parent, icon, description, and order. Folder membership is carried by the owning `library_entry` snapshot. |
| `pick_list_value` | User vocabulary list, optional kind, value, and order. |

The accepted entity set is explicit. Unknown entity types and removed snapshot
or Work/Release anchor payloads are rejected. The App packages entry-owned
images and custom-field values in reserved `personal_data` keys
`__sync_item_images` and `__sync_custom_fields`; Sync treats those keys as
opaque parts of the complete entry snapshot, and the App materializes them into
their local attachment tables on pull. They are not separate Sync entity types.
Loans, folder membership, reading queue position, and user-created external
links are opaque personal attachments in each complete
`library_entry.personal_data` snapshot. Folder definitions are synced as
`user_folder` entities. The App materializes attachments in local tables and
replaces them with each authoritative entry snapshot.

Catalog Item references use `{ "kind": "...", "id": "..." }`. A
`library_entry_ref` uses the same shape but identifies a local entry.
Entry-owned custom fields, images, external links, tracking state, tracking
units, watch sessions, and Music listening events use that local identity and
do not carry a second `catalog_ref`. Wishlist records may target a Catalog Item before a local entry
exists. Nested `target_ref`, `entity_type`,
`root_id`, and `parent_id` values are rejected. Kind-specific episode and
chapter coordinates remain explicit fields in their owning payloads.

## Conflicts and deletes

The service uses last-write-wins by `client_changed_at` within a user's entity
key. A stale write is rejected with the winning payload so the client can
review or retry it. A delete is stored as a tombstone until a newer upsert
replaces it. The append-only change log is retained for
`SYNC_CHANGE_RETENTION_DAYS` (default 90); pruning old changes does not remove
current entity state or tombstones.

## Fresh database setup

Sync creates schema v1 on an empty database path. For a development reset,
stop Sync, retain the old database and its `-wal`/`-shm` sidecars outside the
data directory, and configure the v1 instance with a different empty database
path. Do not deploy or reset a live database as part of this implementation.
