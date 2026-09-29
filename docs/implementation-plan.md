# Collectarr Sync v1 Scope

## Ownership boundary

Collectarr Sync mirrors App-owned personal records between a user's devices. Collectarr Core owns canonical Catalog Items and their real kind-owned children. Sync does not store catalog snapshots, provider IDs, provider envelopes, import jobs, or provider provenance.

The personal record key is scoped by authenticated user, `entity_type`, and `entity_id`. Payload references identify either a catalog target or an owned copy. Deletes remain tombstones; conflict handling remains last-write-wins by client timestamp.

## Supported v1 entities

The supported entity types are defined by `collectarr_sync.schemas.SyncEntityType` and documented in [the protocol contract](protocol-contract.md): owned items, wishlist items, tracking entries and units, watch sessions, custom episodes, metadata overrides, locations, and pick-list values.

`library_item_snapshot` was removed because it copied canonical catalog data into Sync. This does not remove sync for owned copies, wishlist, tracking, sessions, or other supported personal records.

Loans, folders, reading queues, custom-field values, and personal images are not currently cross-device Sync entities. Add each only with an App queue producer, typed v1 payload, apply/retry handling, conflict behavior, and protocol documentation.

## Coordinated reset

The v1 wire contract and SQLite store do not accept the old catalog-snapshot or Work/Release anchor payloads. Do not migrate or reset a deployed database as part of implementation. For a fresh development instance, stop Sync, preserve any existing database and SQLite sidecars as a separate backup, then configure a new empty database path for v1. See [the deployment and reset guide](sync.md).

## Completion checks

- App queue producers and Sync schemas agree on every supported entity and reference.
- User isolation, scoped entity identity, last-write-wins conflicts, and tombstones remain intact.
- No Sync path reads or writes canonical Core catalog data.
- README, this scope, and the protocol contract describe the same supported entity set.
