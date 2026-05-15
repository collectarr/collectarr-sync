# Sync Boundary

Collectarr keeps the central backend metadata-only. The hosted or shared server stores canonical catalog data, provider IDs, images, search indexes, auth/admin identity, and operational state. It does not store a user's owned items, wishlist, purchase dates, prices, grades, notes, tags, or personal shelves.

## Local-First Client

The Flutter app writes personal data to its local Drift database:

- catalog item snapshots for saved library entries
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

Flutter clients read the sync endpoint from Dart defines:

```powershell
flutter run --dart-define=COLLECTARR_SYNC_BASE_URL=http://localhost:8020 --dart-define=COLLECTARR_SYNC_KEY=collectarr-sync-dev-key
```

Use `http://10.0.2.2:8020` for the Android emulator, or the host machine's LAN IP for physical devices.

The Flutter Settings page also has endpoint presets for common local setups:

- local desktop: `http://localhost:8010` and `http://localhost:8020`
- Android emulator: `http://10.0.2.2:8010` and `http://10.0.2.2:8020`
- LAN template: `http://192.168.1.10:8010` and `http://192.168.1.10:8020`

Presets fill the metadata and sync URL fields. Save the settings after applying
a preset, and edit the LAN host IP before saving it for a physical device.

Web builds connect to the personal sync service directly from the browser.
Browser CORS, HTTPS, and local-network rules can block web sync even when the
same endpoint works from desktop or mobile. The central metadata server still
does not store private collection data as a fallback.

## Pairing Devices

The Flutter Settings page can copy a pairing code, show the same code as a QR
payload, and apply a pasted pairing code on another device. The code contains
only connection settings:

- metadata API URL
- personal sync service URL
- personal sync key

It does not include the local `device_id`. Each app installation keeps its own
stable device identity so sync can distinguish the devices that wrote changes.

For LAN setups, copy the pairing code from the configured desktop device and
apply it on the phone after editing the host IP if needed. QR scanning can be
added later, but manual copy/paste and QR rendering are enough for the MVP.

## Backup And Restore

The sync service stores personal library state, so back it up separately from
the central metadata server.

Docker volume backup:

```powershell
docker compose --profile sync stop sync
docker compose --profile sync cp sync:/data ./collectarr-sync-data
Compress-Archive -Path .\collectarr-sync-data\* -DestinationPath .\collectarr-sync-data.zip -Force
docker compose --profile sync start sync
```

Docker volume restore:

```powershell
Expand-Archive .\collectarr-sync-data.zip -DestinationPath .\collectarr-sync-data-restore -Force
docker compose --profile sync stop sync
docker compose --profile sync run --rm --entrypoint sh sync -lc "rm -rf /data/*"
docker compose --profile sync cp ./collectarr-sync-data-restore/. sync:/data
docker compose --profile sync start sync
```

Local SQLite backup:

1. Stop `collectarr-sync`.
2. Copy the SQLite database file and its `-wal` and `-shm` sidecar files if
   they exist.
3. Restart `collectarr-sync`.
4. After restore, run `GET /status` and check the entity, tombstone, and change
   counts before syncing another device.

Because clients keep local snapshots too, a restore can surface stale-client
conflicts. Flutter Settings lists rejected sync changes and lets the user choose
between keeping the service version or queuing the current local version to
overwrite the service on the next sync.

## Contract

The current service uses a diff-oriented shape:

- `POST /sync/push`
- `POST /sync/pull`
- `GET /sync/changes?since=...`

Suggested sync fields:

- `device_id`: stable client installation identifier
- `client_changed_at`: timestamp assigned by the client
- `changed_at`: service timestamp assigned when a change is accepted
- `entity_type`: `library_item_snapshot`, `owned_item`, `wishlist_item`, `note`, or future local entities
- `action`: `upsert` or `delete`
- `payload`: entity-specific local data

Initial conflict policy is last-write-wins, with tombstones for deletes. When a
push is rejected because the service has a newer client timestamp, Flutter keeps
the service version by default but can enqueue a fresh local retry from Settings
when the local device should win.

Rejected push responses include the service action and service payload that won
the conflict. Flutter attaches the rejected local queued payload before showing
the conflict review, so Settings can display a side-by-side local vs service
diff without calling Collectarr Core.

Full pulls return the current entity state only. Incremental pulls with `since` return both current entities changed since that timestamp and the ordered change records for that window.

The append-only `changes` log is retained for `SYNC_CHANGE_RETENTION_DAYS` days, defaulting to 90. Pruned changes do not remove current entity state or delete tombstones.

`library_item_snapshot` stores the catalog metadata needed to render a user's saved item on another device without calling the central Collectarr Core again. The snapshot is intentionally client-owned sync data, not canonical provider metadata. A typical payload includes:

- `snapshot_version`
- `kind`
- `title`
- `item_number`
- `synopsis`
- `cover_image_url`
- `thumbnail_image_url`
- `publisher`
- `release_date`
- `release_year`
- `barcode`
- `variant`

### Push Example

```json
{
  "device_id": "desktop",
  "changes": [
    {
      "entity_type": "library_item_snapshot",
      "entity_id": "comic-1",
      "action": "upsert",
      "client_changed_at": "2026-05-11T09:59:59Z",
      "payload": {
        "snapshot_version": 1,
        "kind": "comic",
        "title": "Absolute Batman",
        "item_number": "1",
        "cover_image_url": "https://cdn.example/absolute-batman-1.jpg",
        "thumbnail_image_url": "https://cdn.example/absolute-batman-1-thumb.jpg",
        "publisher": "DC",
        "release_year": 2024
      }
    },
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
