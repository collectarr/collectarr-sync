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

## Personal Sync Service

Multi-device personal sync lives in a separate opt-in service named `collectarr-sync`.

That service is user-hosted and can expose the user's personal database to their own devices:

- desktop app writes local changes
- Android app writes local changes
- optional web client connects to the user's own sync service
- central `collectarr` metadata server remains unaware of personal collection state

## Running Locally

```powershell
Copy-Item .env.example .env
docker compose --profile sync up --build sync
```

The service listens on http://localhost:8020 by default and stores data in the `sync_data` Docker volume. Requests to `/sync/*` require:

```http
X-Collectarr-Sync-Key: collectarr-sync-dev-key
```

Change `SYNC_API_KEY` before exposing the service outside your local network.

## Contract

The current service uses a diff-oriented shape:

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

### Push Example

```json
{
  "device_id": "desktop",
  "changes": [
    {
      "entity_type": "owned_item",
      "entity_id": "owned-1",
      "action": "upsert",
      "client_changed_at": "2026-05-11T10:00:00Z",
      "payload": {
        "item_id": "comic-1",
        "condition": "Near Mint",
        "grade": "9.8"
      }
    }
  ]
}
```

### Pull Example

```json
{
  "since": "2026-05-11T00:00:00Z"
}
```
