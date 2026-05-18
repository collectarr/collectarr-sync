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
