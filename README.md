# Collectarr Sync

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/collectarr/collectarr-sync)](https://github.com/collectarr/collectarr-sync/releases)
[![Issues](https://img.shields.io/github/issues/collectarr/collectarr-sync)](https://github.com/collectarr/collectarr-sync/issues)
![Python](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)

Collectarr Sync is the optional self-hosted service for **App-owned library
entries and personal state**. It provides device-aware push/pull, conflict
responses, tombstones, change history, pairing and explicit collection sharing.

Core owns the canonical shared catalog. Sync carries complete local entry
snapshots, including their catalog and personal maps; it does not search Core,
interpret kind-owned catalog fields or become a second canonical catalog.

## Protocol and storage

The wire protocol and SQLite schema are **version 1**. Each entity/change is scoped
by authenticated user, entity type and stable local identity. A library entry's
optional Core reference is provenance, not its sync identity.

- `library_entry` carries `kind`, `catalog_data`, `personal_data`, timestamps and
  optional `source_catalog_ref`.
- Explicit personal entities carry tracking, units, watch/listening sessions,
  custom episodes, vocabulary, location and folder definitions where supported.
- The App packs images and custom fields into reserved entry personal keys and
  materializes them on pull. Loans, folder membership, queue position and local
  links are also entry-owned attachments, not standalone canonical entities.
- Kind-owned maps remain opaque to Sync; supported envelopes and entity types
  are validated explicitly.
- Stale writes are rejected with the winning service state. Conflict ordering
  uses `client_changed_at`; clients must keep timestamps and review conflicts.
- Deletes become tombstones. Change-log retention defaults to 90 days; pruning
  history does not remove current entities or tombstones.

See [protocol-contract.md](docs/protocol-contract.md) for the exact accepted
payloads. The current schema is created on a new, empty SQLite database path;
there is no runtime upgrade or old-payload adapter.

## Local development

Use **Python 3.14+**, matching the package and CI:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pip check
$env:SYNC_API_KEY='collectarr-sync-dev-key'
$env:SYNC_DATABASE_PATH='./collectarr-sync-dev.db'
python -m uvicorn collectarr_sync.main:app --host 127.0.0.1 --port 8020 --reload
```

The service initializes its SQLite schema at startup. Choose a new development
path; keep existing databases and backups untouched. Bind to `0.0.0.0` when a LAN
device needs access and configure its reachable URL.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health, protocol/schema versions |
| `POST /sync/push` | Push supported changes |
| `POST /sync/pull` | Pull current state, optionally since a timestamp |
| `GET /sync/changes` | Ordered retained changes |
| `GET /sync/status` | Authenticated user's counts/status |
| `GET /sync/devices` / `DELETE /sync/devices/{device_id}` | Device listing/removal |
| `GET /sync/pairing-code` | API-key-protected connection pairing payload |
| `/docs` | Swagger API reference |

Local service: http://localhost:8020. Docs: http://localhost:8020/docs.

## Docker

```powershell
docker build -t collectarr-sync .
docker run --rm -p 8020:8020 `
  -e SYNC_API_KEY=collectarr-sync-dev-key `
  -e SYNC_DATABASE_PATH=/data/collectarr-sync.db `
  -e SYNC_PUBLIC_BASE_URL=http://localhost:8020 `
  -v collectarr_sync_data:/data `
  collectarr-sync
```

Keep the database inside the persistent volume. Set `SYNC_PUBLIC_BASE_URL` to the
address devices can actually reach; pairing uses it. Core's sibling development
stack can also launch Sync through `tools/dev.ps1 start -WithSync`.

## Configuration and authentication

[collectarr_sync/config.py](collectarr_sync/config.py) defines the active settings:

| Setting | Purpose |
| --- | --- |
| `SYNC_DATABASE_PATH` | SQLite file location |
| `SYNC_API_KEY` | Shared-key authentication |
| `SYNC_JWT_SECRET` | Enables HS256 bearer-token authentication |
| `SYNC_PUBLIC_BASE_URL` | Advertised connection/pairing URL |
| `SYNC_CHANGE_RETENTION_DAYS` | Retained change history, default 90 |
| `ENVIRONMENT` | Development/test versus deployed configuration |
| `CORS_ORIGINS` | Allowed browser origins as a JSON array |

The `X-Collectarr-Sync-Key` header authenticates the single default partition.
It does not distinguish multiple users. Per-user bearer tokens require
`SYNC_JWT_SECRET` and a non-empty `sub`; that subject identifies the user's
partition. Pairing-code generation is API-key-only because its payload contains
the shared key. Core sign-in alone is not proof of a personal sync session.

For a non-development deployment, configure a non-default key, the intended
per-user authentication and the browser origins you serve. The service is
self-hosted; its authentication and public URL must match your deployment.

App development defaults can be supplied at build time:

```powershell
flutter run `
  --dart-define=COLLECTARR_SYNC_BASE_URL=http://localhost:8020 `
  --dart-define=COLLECTARR_SYNC_KEY=collectarr-sync-dev-key
```

App also exposes **Settings → Connection**. An Android emulator reaches the host
via `10.0.2.2`; other devices need a LAN/public address rather than their own
localhost.

## Collection sharing

Sharing publishes an explicit client-built snapshot independently of personal
sync. Saving Cloud Sharing settings in App republishes that collection; later
personal sync updates do **not** automatically refresh a publication.

| Endpoint | Purpose |
| --- | --- |
| `GET /sharing?kind=music` | Owner's sharing settings |
| `PUT /sharing/{collection_id}` | Replace owner's snapshot/visibility |
| `GET /public` | Public collection directory |
| `GET /public/{token}` | Public or enabled private-link collection viewer |

Partial visibility is public without personal fields. Public visibility can
include personal fields explicitly. Private visibility revokes publication unless
an optional private link is enabled; those links are absent from the directory.
Personal inclusion is explicit, and access-mode changes rotate tokens.

Snapshots have a 10,000-item and 5 MB serialized limit. See
[collection-sharing.md](docs/collection-sharing.md) for visibility, revocation
and validation details.

## Checks and backups

```powershell
$env:ENVIRONMENT='test'
$env:SYNC_API_KEY='test-sync-key'
python -m ruff check .
python -m pytest
```

Tests cover the service against their configured isolated storage; Core/PostgreSQL
are not required for Sync's SQLite contract tests. The exact CI gate is in
[tests.yml](.github/workflows/tests.yml).

Stop Sync before copying a database backup. Preserve the SQLite file and any
`-wal`/`-shm` sidecars together. Store the backup outside the mounted data directory.
Restore with the service stopped, using the supported schema. A flat CSV export
from App is not a Sync database backup. See [deployment and backup](docs/sync.md).

## Troubleshooting

- **401 responses:** check shared key or bearer token/secret/subject; they select
  different authentication paths.
- **Missing data after recreation:** check persistent volume and database path.
- **Pairing URL unreachable:** check public base URL, bind address, firewall and
  browser CORS; localhost on another device means that device itself.
- **Repeated conflicts:** inspect the returned winning state and client timestamp
  rather than blindly retrying the same stale write.
- **Shared page out of date:** republish from App's Cloud Sharing page; sync alone
  does not refresh it.

## Releases and related projects

Pushes to `main` run CI. Release/container publishing responds to manual dispatch
or a published GitHub release, with build-only/existing-release modes defined in
[release.yml](.github/workflows/release.yml). Images are published under
`ghcr.io/collectarr/collectarr-sync`; choose versions from
[GitHub Releases](https://github.com/collectarr/collectarr-sync/releases).

| Repository | Responsibility |
| --- | --- |
| [collectarr-app](https://github.com/collectarr/collectarr-app) | Local library, personal records, sync queue, conflict UI and snapshot publication |
| [collectarr-core](https://github.com/collectarr/collectarr-core) | Canonical catalog, source-neutral proposals/corrections, search and images |
| `collectarr-site` | Separate product website and shared user manual, prepared locally |

**Help → User Manual** in App opens the shared manual's kind chapter. Initial
website publication is pending. Protocol/deployment references in this repository
are developer documentation, separate from that end-user guide. Dated
[current-status.md](docs/current-status.md) reports are historical evidence;
implementation and protocol sources remain authoritative.

## Support

[![Support on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/saitatter)
