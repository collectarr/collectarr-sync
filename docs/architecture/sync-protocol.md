# Current Music sync protocol

## Ownership boundary

Collectarr Sync stores App-owned library entries and personal state between a
user's devices. Each `library_entry` is one complete, independently editable
local record. Core provenance is optional and represented by
`source_catalog_ref`; the entry does not depend on a separate Catalog Item at
another device. Catalog data, personal data, and timestamps travel together in
the entry payload. Canonical Core data is never written to or read from Sync as
a separate entity.

The record key is scoped by authenticated user, `entity_type`, and
`entity_id`. Updates use last-write-wins by the client timestamp. Deletes are
tombstones. Retries can use `client_change_id` for idempotency. User isolation
applies to the current entity, change log, status, device history, and device
removal operations.

## Supported protocol

The supported entity types and exact payloads are maintained in
[`protocol-contract.md`](protocol-contract.md) and validated in
`collectarr_sync.schemas`. The App producers, Sync validators, pull/apply path,
and retry mapper must agree on every entity before it is advertised as a
cross-device feature.

Personal entry data stays in `library_entry.personal_data`. Standalone history
records may use `library_entry_ref` when they target one specific local entry.
Catalog-origin metadata is represented only by `source_catalog_ref` in the
entry envelope. Sync does not accept Work/Release nodes, nested target paths,
provider IDs, provider snapshots, or ingest jobs.

## Coordinated reset

Wire protocol v1 and the SQLite schema v1 are created on a new, empty database
path. Do not migrate, overwrite, or delete an existing deployment database as
part of implementation. For a fresh development instance, stop Sync, preserve
the old database and any SQLite sidecars separately, then configure a new
empty path. See [`sync.md`](sync.md) for the operational setup.

## Completion checks

- App queue producers send complete `library_entry` payloads.
- Push, pull, retries, conflicts, and tombstones preserve the entry identity
  and complete payload.
- User isolation remains enforced for every operation.
- Sync does not store canonical Core catalog entities as separate records.
- README and both protocol documents describe the same supported entity set.

## Release baseline

The first release accepts Music references only. New databases use baseline 1; existing unversioned databases are not modified automatically. All future persistent changes require explicit ordered, data-preserving migrations. The complete Music payload shape remains unchanged.
