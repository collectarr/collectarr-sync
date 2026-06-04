# Collectarr Sync

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![GitHub Release](https://img.shields.io/github/v/release/collectarr/collectarr-sync)
[![Issues](https://img.shields.io/github/issues/collectarr/collectarr-sync)](https://github.com/collectarr/collectarr-sync/issues)
![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Docker%20%7C%20Self--Hosted-2496ED?logo=docker&logoColor=white)

> Optional personal sync service for Collectarr: device-aware push/pull APIs, conflict review, tombstones, and backup-friendly storage.

Collectarr Sync keeps personal shelf state in sync between a user's devices. It
does not fetch provider metadata and it does not own the canonical catalog.
Shared metadata stays in `collectarr-core`, while the user's local-first shelf
state continues to live in `collectarr-app`.

---

## ✨ Features

### 🔄 Personal Sync Protocol

- Authenticated push, pull, changes, status, and device APIs
- Sync protocol and schema version tracking so clients can reason about compatibility
- Personal collection entities, catalog snapshots, tombstones, and bounded change logs stored in SQLite
- Explicit service health and retention reporting instead of opaque background state

### 📱 Device Identity And Conflict Handling

- Stable device identity for multi-device sync and pairing flows
- Rejection of stale local writes when another device already committed newer state
- Conflict payloads detailed enough for `collectarr-app` to review and recover instead of silently overwriting data
- Personal-data-only scope so Sync never turns into a second metadata backend

### 🧰 Operations And Backup

- Simple FastAPI deployment for local LAN or self-hosted Docker usage
- Backup and restore guidance for the SQLite database and mounted Docker volume
- Minimal service surface built for personal use rather than multi-tenant SaaS behavior
- Clear repo boundary relative to `collectarr-app` and `collectarr-core`

---

## 🚀 Quick Start

### Local development setup

```powershell
python -m pip install -e .[dev]
python -m ruff check .
python -m pytest
```

### Run locally

```powershell
$env:SYNC_API_KEY="dev-sync-key"
uvicorn collectarr_sync.main:app --host 0.0.0.0 --port 8020 --reload
```

### Run with Docker

```powershell
docker build -t collectarr-sync .
docker run --rm -p 8020:8020 `
  -e SYNC_API_KEY=dev-sync-key `
  -e SYNC_DATABASE_PATH=/data/collectarr-sync.db `
  -v collectarr_sync_data:/data `
  collectarr-sync
```

### Local URLs

| Service | URL |
|---------|-----|
| Sync API | http://localhost:8020 |
| Sync docs (Swagger) | http://localhost:8020/docs |

---

## 🧱 Repository Boundary

This repository owns sync push/pull/change APIs, sync storage, device identity,
pairing protocol support, tombstones, conflict handling, and backup / restore
docs.

It deliberately does not own:

- canonical metadata ingest
- provider search
- catalog editorial workflows
- local collection UX

Those responsibilities stay split across the other Collectarr repos.

---

## 🔄 Releases

Release publishing is manual-only. The `Release` GitHub Actions workflow uses
`workflow_dispatch`; pushing to `main` runs CI only.

When a releasable version is detected, the workflow publishes a GitHub Release
and pushes the sync container image to `ghcr.io/collectarr/collectarr-sync`
with both the semantic version tag and `latest`.

---

## 🛠 Troubleshooting

- **Sync requests are rejected immediately**: verify `SYNC_API_KEY` matches what `collectarr-app` is configured to send.
- **State disappears after container recreation**: mount a persistent Docker volume and keep `SYNC_DATABASE_PATH` inside that volume.
- **Pairing works on one machine but not over LAN**: bind the service to a reachable host/IP and confirm the client can reach port `8020` through local firewall rules.
- **Conflicts keep reappearing**: inspect the returned stale-change details in the app and resolve with a deliberate keep-local / keep-service / retry flow instead of repeated blind retries.

---

## 🔗 Related Repos

| Repo | Purpose |
|------|---------|
| `collectarr-app` | Flutter client that owns local-first shelf state and conflict review UX |
| `collectarr-core` | Canonical metadata catalog, provider ingest, and admin server |

## 🧭 Library Parity Contract

See [docs/library-parity-contract.md](docs/library-parity-contract.md) for Sync
compatibility guarantees against the shared Core contract.

## 🗺️ Current Focus

See [docs/implementation-plan.md](docs/implementation-plan.md) for the active
Sync roadmap.

Near-term Sync work:

- make pairing reliable enough for MVP with manual code, QR render, and clear LAN setup docs
- deepen conflict actions beyond review: keep service, keep local, retry local, and surface stale-client causes clearly
- harden backup/restore around the SQLite database, WAL files, and service health checks
- publish stable sync payload schemas for `collectarr-app`
- keep the service intentionally personal-data-only; it should never fetch provider metadata or become a catalog mirror

---

## Support

If Collectarr is useful to you, you can support ongoing development on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/saitatter)
