# Collectarr Sync

Collectarr Sync is the optional personal sync service for Collectarr.

It syncs local personal-library snapshots between a user's devices. It is not a
metadata provider and does not own the canonical catalog.

## Development

```powershell
python -m pip install -e .[dev]
python -m ruff check .
python -m pytest
```

Run locally:

```powershell
$env:SYNC_API_KEY="dev-sync-key"
uvicorn collectarr_sync.main:app --host 0.0.0.0 --port 8020 --reload
```

Run with Docker:

```powershell
docker build -t collectarr-sync .
docker run --rm -p 8020:8020 `
  -e SYNC_API_KEY=dev-sync-key `
  -e SYNC_DATABASE_PATH=/data/collectarr-sync.db `
  -v collectarr_sync_data:/data `
  collectarr-sync
```

## Repository Boundary

This repository owns:

- sync push/pull/change APIs
- sync storage
- device identity and pairing protocol
- tombstones and conflict handling
- sync backup/restore docs

Related repositories:

- `collectarr/collectarr-core`: metadata catalog and provider ingest server
- `collectarr/collectarr-app`: Flutter local-library client

## Current Focus

See [docs/implementation-plan.md](docs/implementation-plan.md) for the active
Sync roadmap.

Near-term Sync work:

- make pairing reliable enough for MVP: manual code, QR render, and clear LAN
  setup docs
- deepen conflict actions beyond review: keep service, keep local, retry local,
  and surface stale-client causes clearly
- harden backup/restore around the SQLite database, WAL files, and service
  health checks
- version the sync protocol and publish stable payload schemas for
  `collectarr-app`
- keep the service intentionally personal-data-only; it should never fetch
  provider metadata or become a catalog mirror
