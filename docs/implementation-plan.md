# Collectarr Sync Implementation Plan

Sync owns optional, user-hosted personal library sync. It stores personal
snapshots and conflict state for a user's devices. It does not own provider
metadata, canonical catalog records, or image/provider ingest.

## Done

- Split from the original monorepo into `collectarr/collectarr-sync`.
- CI runs Python lint/tests.
- FastAPI sync service exposes push/pull/status/devices/change APIs.
- SQLite-backed storage, migrations, tombstones, conflicts, and stale-write
  rejection exist.
- Basic API-key authentication exists.
- Documentation explains the metadata-only Core boundary and local-first App
  model.
- Generic entity-type sync payloads already support personal metadata alongside
  owned/wishlist state, including synced location definitions.

## MVP Priorities

1. ~~Protocol contract~~ ✅
   - ~~Add an explicit sync protocol version to status/pairing responses.~~
   - ~~Publish payload schemas for library snapshots, tombstones, conflicts, and
     pairing codes.~~
   - ~~Keep backwards-compatibility notes for App releases.~~

2. ~~Pairing and device management~~ ✅
   - ~~Keep manual pairing code as the reliable MVP path.~~
   - ~~Support QR render/scan from App when platform support is ready.~~
   - ~~Surface known devices, last-seen timestamps, and revoke/remove actions.~~

3. ~~Conflict handling~~ ✅
   - ~~Make server conflict payloads easy for App to diff: local rejected payload,
     service payload, timestamps, device IDs, and action reason.~~
   - ~~Support App actions: keep service, retry local, dismiss, and inspect raw
     payload.~~
   - ~~Add tests for multi-device stale writes and retry-after-conflict flows.~~

4. ~~Backup and restore~~ ✅
   - ~~Document Docker volume and direct SQLite backup/restore.~~
   - ~~Add a service health check that reports entity/change/tombstone counts.~~
   - ~~Add restore warnings for stale clients and expected conflict behavior.~~

5. ~~Deployment hardening~~ ✅
   - ~~Require non-default `SYNC_API_KEY` outside development/test.~~
   - ~~Document HTTPS/LAN/reverse-proxy and CORS requirements.~~
   - ~~Add Docker image publishing once release flow is set.~~

## Post-MVP

- Optional per-user accounts if one Sync instance serves multiple people.
  - If this lands, keep the single-user/self-host path simple; multi-user support should layer on top rather than complicate pairing for the common case.
  - Scope accounts around isolated datasets, device ownership, and admin-only maintenance actions before expanding into richer auth UX.
- Encrypted payload mode or pluggable secret handling.
  - Prefer an additive mode where operators can choose envelope encryption or external secret providers without breaking the plain self-hosted path.
  - Preserve conflict inspection/debuggability expectations; encrypted mode must still make restore and stale-write handling operable.
- Retention policies for old changes/tombstones.
  - Define retention separately for audit visibility, pull safety windows, and storage cleanup so old devices do not silently lose reconciliation context.
  - Expose retention policy warnings in status/admin surfaces before destructive cleanup is enabled.
- Export/import endpoint for full sync database snapshots.
  - Treat this as a real migration/backup surface: include version metadata, integrity checks, and explicit restore warnings for stale clients.
  - Keep snapshot export/import separate from the normal sync protocol so bulk recovery does not distort per-change conflict semantics.
