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

## MVP Priorities

1. Protocol contract
   - Add an explicit sync protocol version to status/pairing responses.
   - Publish payload schemas for library snapshots, tombstones, conflicts, and
     pairing codes.
   - Keep backwards-compatibility notes for App releases.

2. Pairing and device management
   - Keep manual pairing code as the reliable MVP path.
   - Support QR render/scan from App when platform support is ready.
   - Surface known devices, last-seen timestamps, and revoke/remove actions.

3. Conflict handling
   - Make server conflict payloads easy for App to diff: local rejected payload,
     service payload, timestamps, device IDs, and action reason.
   - Support App actions: keep service, retry local, dismiss, and inspect raw
     payload.
   - Add tests for multi-device stale writes and retry-after-conflict flows.

4. Backup and restore
   - Document Docker volume and direct SQLite backup/restore.
   - Add a service health check that reports entity/change/tombstone counts.
   - Add restore warnings for stale clients and expected conflict behavior.

5. Deployment hardening
   - Require non-default `SYNC_API_KEY` outside development/test.
   - Document HTTPS/LAN/reverse-proxy and CORS requirements.
   - Add Docker image publishing once release flow is set.

## Post-MVP

- Optional per-user accounts if one Sync instance serves multiple people.
- Encrypted payload mode or pluggable secret handling.
- Retention policies for old changes/tombstones.
- Export/import endpoint for full sync database snapshots.
