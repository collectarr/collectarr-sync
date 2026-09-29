# Collectarr Sync

Collectarr Sync mirrors App-owned personal state between a user's devices. Core owns canonical catalog records and exposes the source-neutral catalog API; Sync does not receive catalog snapshots, provider IDs, provider envelopes, or import/ingest jobs.

The current protocol and SQLite schema are both version 1. The supported personal entity list, reference shape, conflict policy, and removed legacy payloads are defined in [the protocol contract](protocol-contract.md).

## Run locally

```powershell
$env:SYNC_API_KEY="collectarr-sync-dev-key"
$env:SYNC_DATABASE_PATH=".\data\collectarr-sync-v1.db"
uvicorn collectarr_sync.main:app --host 0.0.0.0 --port 8020 --reload
```

The development API key supports one local user partition. Configure user authentication for deployments shared by multiple accounts. Requests to `/sync/*` require the configured Sync key or the configured user bearer token.

Docker example:

```powershell
docker build -t collectarr-sync .
docker run --rm -p 8020:8020 `
  -e SYNC_API_KEY=collectarr-sync-dev-key `
  -e SYNC_DATABASE_PATH=/data/collectarr-sync-v1.db `
  -v collectarr_sync_v1_data:/data `
  collectarr-sync
```

Flutter clients receive the endpoint through Dart defines:

```powershell
flutter run --dart-define=COLLECTARR_SYNC_BASE_URL=http://localhost:8020 --dart-define=COLLECTARR_SYNC_KEY=collectarr-sync-dev-key
```

For an Android emulator use `http://10.0.2.2:8020`; for another device use the host's LAN address. Web clients also need browser CORS and local-network access.

## Coordinated v1 setup

The v1 payloads intentionally reject the earlier catalog snapshot and Work/Release anchor formats. Before adopting this version with an existing local Sync database, stop the service and copy the database plus any SQLite sidecars to a dated backup outside its data directory. Configure v1 to use a new, empty database path and pair the App clients with that service. Do not delete or overwrite the prior database, reset a deployed database, or treat an old-format backup as a v1 backup. Keep the old backup separately for manual recovery.

App and Core require their own coordinated v1 setup instructions; this Sync procedure does not reset or migrate either repository's database.

## Backup

Stop Sync before copying its SQLite database. Include the database file and its `-wal` and `-shm` files if present. Store the copy outside the service data directory and label it with the Sync protocol/schema version. A backup from an older protocol is not directly restorable into v1.

## Protocol behavior

- User partitioning isolates each account's entities and change log.
- Conflicts use last-write-wins by the client timestamp; rejected writes include the service state.
- Deletes remain as tombstones until a newer upsert replaces them.
- The ordered change log is retained for 90 days by default; current entity state remains after log pruning.
- Sync mirrors personal records only. Canonical catalog search, edits, covers, and proposals go through Core/App flows.

See [protocol-contract.md](protocol-contract.md) for exact entity payloads and endpoint shapes.
