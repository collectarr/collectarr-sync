# Collectarr Sync

Keep your Music and Comics libraries in step across devices, and share selected
collections on your terms. Sync is the optional self-hosted companion to
Collectarr.

**License:** [GNU AGPLv3 only](LICENSE) (`AGPL-3.0-only`). See the
[contribution guide](CONTRIBUTING.md) for development and licensing terms,
including the historical MIT notice.

**Protocol version 1 supports Music and Comics.** Existing payload shapes and
behavior remain the v1 baseline; there is no rollback to an older protocol or
schema.

## Your collection, wherever you use it

- Synchronize complete personal library-entry snapshots between devices.
- Keep catalog copies and personal fields together without becoming a catalog
  provider itself.
- Isolate users and devices; handle repeated pushes and deleted entries safely.
- Publish selected collection snapshots with explicit visibility choices.
- Share a limited public view or create a revocable private sharing link.
- Keep private notes and other personal fields out unless explicitly selected.

Use [Collectarr App](https://github.com/collectarr/collectarr-app) for the library
experience and [Core](https://github.com/collectarr/collectarr-core) for canonical
catalog information.

## Self-hosting

Run the published container image, `ghcr.io/collectarr/collectarr-sync`, which
listens on port 8020. See [Sync](docs/sync.md) for configuration and running it
locally, and [collection sharing](docs/collection-sharing.md) for visibility and
private links. Configure authentication before exposing the service outside
development.

## Predictable upgrades

Sync stores personal snapshots, not Core catalog tables. Future persistence
changes require explicit ordered migrations; supported data must survive
upgrades. A fresh baseline is for the initial v1 installation, never a shortcut
for upgrading an existing user database.

## Independent by design

Sync is part of Collectarr's independent **clean-room implementation inspired by
CLZ collection workflows**. It is not affiliated with or endorsed by CLZ, and
includes no CLZ source code, catalog dataset or proprietary assets.

## Development

Use Python 3.14 and follow [Sync](docs/sync.md) and the
[protocol contract](docs/protocol-contract.md). Read [AGENTS.md](AGENTS.md) for
data ownership, isolated testing and migration requirements.
