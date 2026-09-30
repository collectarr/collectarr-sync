# Sync Protocol Contract v1

## Purpose and boundaries

Collectarr Sync stores App-owned personal state only. Core remains the source-neutral catalog API. Sync never stores or distributes canonical catalog records, catalog snapshots, provider identifiers, provider envelopes, ingest jobs, or provider provenance.

Each change is scoped by the authenticated Sync user, `entity_type`, and `entity_id`. A catalog reference is serialized as `{ "kind": "...", "entity_type": "...", "id": "..." }`, with optional `root_id` and `parent_id` when a kind-owned child reference needs its structural context. Sync treats those identifiers as opaque and does not impose a shared Work/Release hierarchy. An owned-copy reference is `{ "kind": "...", "id": "..." }`.

## Version

The current wire protocol is version 1. The current SQLite store schema is also version 1.

```http
GET /health
```

```json
{ "status": "ok", "protocol_version": 1, "schema_version": 1 }
```

A fresh v1 deployment is required for this protocol. Older personal payload formats are unsupported after the coordinated cutover.

## Authentication and isolation

Sync authenticates each request and partitions stored entities and changes by the authenticated user. A user's devices can only read, overwrite, or delete rows in that user's partition. Deployments must configure per-user authentication; a shared development key is suitable only for a single-user local instance.

## Endpoints

- `POST /sync/push` accepts personal changes.
- `POST /sync/pull` returns the current entities, optionally since a timestamp.
- `GET /sync/changes?since=...` returns the ordered change log.
- `GET /sync/status` returns counts for the authenticated user.

Each pushed change has `entity_type`, `entity_id`, `action` (`upsert` or `delete`), `client_changed_at`, and a typed personal `payload`. Deletes use a tombstone and may send an empty payload.

## Supported personal entities

`owned_copy` represents an App-owned copy as a first-class Sync entity. It carries the copy's personal fields and a reference to its Core Catalog Item. Catalog records remain owned by Core; Sync carries owned copies, wishlist entries, tracking, sessions, and other explicitly supported personal state.

| Entity type | Payload identity and contents |
|---|---|
| `owned_copy` | `catalog_ref`, an optional `target_ref` only when that kind has a distinct owned target below the Catalog Item, and the user's copy fields such as condition, purchase details, location, notes, and kind-owned copy details. Music copies target one concrete album Catalog Item and omit `target_ref`. |
| `wishlist_item` | `catalog_ref`, target price, currency, notes, and creation time. |
| `tracking_entry` | `catalog_ref`, optional `owned_ref`, status, rating, dates, progress, notes, and kind-owned progress fields. |
| `tracking_unit` | `catalog_ref`, optional `owned_ref` and `tracking_entry_id`, completion time, plus kind-owned unit coordinates. |
| `watch_session` | `catalog_ref`, watch time, source, rating, notes, and kind-owned episode coordinates. |
| `custom_episode` | `catalog_ref` and the user's custom episode fields. |
| `metadata_override` | `target_ref`, `field_key`, and the user's override value. |
| `location` | User-owned location name, parent, description, and order. |
| `pick_list_value` | User vocabulary list, optional kind, value, and order. |

The accepted entity set is explicit. Unknown entity types and removed snapshot or anchor payloads are rejected. Loans, folders, reading queues, custom-field values, and personal images must be added to this contract together with their App queue producers before they can be advertised as cross-device Sync features.

Tracking entries, tracking units, and watch sessions require `catalog_ref`. The removed `target_ref` spelling is not accepted as an alias; kind-specific episode and chapter coordinates remain separate payload fields.

## Conflict handling and deletes

The service uses last-write-wins by `client_changed_at` within a user's entity key. A stale write is rejected with the winning service payload so the client can review or retry it. A delete is stored as a tombstone until a newer upsert replaces it. The append-only change log is retained for `SYNC_CHANGE_RETENTION_DAYS` (default 90); pruning old changes does not remove current entity state or tombstones.

## Reset and backup

Sync creates only the v1 schema on a new, empty database path. To adopt v1 in development, stop Sync, retain the existing database and any `-wal`/`-shm` sidecars outside the data directory, then configure the v1 instance with a different empty database path. Do not point a live deployment at the new schema or remove an existing database as part of this implementation.
