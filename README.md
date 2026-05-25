# Collectarr Sync

Collectarr Sync is the optional personal sync service for Collectarr.

It syncs local personal-library snapshots between a user's devices. It is not a
metadata provider and does not own the canonical catalog; shared metadata stays
in `collectarr-core`, while the user's shelf state stays local-first in
`collectarr-app`.

## What It Does

- Exposes authenticated sync push, pull, changes, status, and devices APIs.
- Stores personal collection entities, catalog snapshots, tombstones, and a
  bounded change log in SQLite.
- Tracks sync protocol and schema versions so App can reason about compatible
  clients.
- Preserves device identity for multi-device sync and pairing flows.
- Rejects stale local changes when another device has already written newer
  state, then returns enough detail for App to review conflicts.
- Reports service health, entity counts, tombstone counts, and retention
  settings.
- Documents backup and restore for the sync SQLite database and Docker volume.

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

## Release Policy

Release publishing is manual-only. The `Release` GitHub Actions workflow uses
`workflow_dispatch`; pushing to `main` runs CI only.

When a releasable version is detected, the workflow publishes a GitHub Release
and pushes the sync container image to `ghcr.io/collectarr/collectarr-sync`
with both the semantic version tag and `latest`.

## Repository Boundary

This repository owns sync push/pull/change APIs, sync storage, device identity,
pairing protocol support, tombstones, conflict handling, and sync backup/restore
docs.

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
- publish stable sync payload schemas for `collectarr-app`
- keep the service intentionally personal-data-only; it should never fetch
  provider metadata or become a catalog mirror

---

## Support

If Collectarr is useful to you, you can support ongoing development on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/saitatter)
