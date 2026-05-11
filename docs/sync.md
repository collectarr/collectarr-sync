# Sync Boundary

Collectarr keeps the central backend metadata-only. The hosted or shared server stores canonical catalog data, provider IDs, images, search indexes, auth/admin identity, and operational state. It does not store a user's owned items, wishlist, purchase dates, prices, grades, notes, tags, or personal shelves.

## Local-First Client

The Flutter app writes personal data to its local Drift database:

- owned items
- wishlist entries
- condition and grading
- purchase date and price
- personal notes
- local delete markers

This lets Android, desktop, and web builds work offline without sending private collection state to the central metadata server.

## Future Personal Sync Service

Multi-device personal sync should be implemented as a separate opt-in service, tentatively named `collectarr-sync`.

That service is user-hosted and can expose the user's personal database to their own devices:

- desktop app writes local changes
- Android app writes local changes
- optional web client connects to the user's own sync service
- central `collectarr` metadata server remains unaware of personal collection state

## Planned Contract

The future `collectarr-sync` service can use the previous diff-oriented shape:

- `POST /sync/push`
- `POST /sync/pull`
- `GET /sync/changes?since=...`

Suggested sync fields:

- `device_id`: stable client installation identifier
- `client_changed_at`: timestamp assigned by the client
- `changed_at`: service timestamp assigned when a change is accepted
- `entity_type`: `owned_item`, `wishlist_item`, `note`, or future local entities
- `action`: `upsert` or `delete`
- `payload`: entity-specific local data

Initial conflict policy should remain last-write-wins, with tombstones for deletes. Manual conflict resolution can come later once the local model stabilizes.
