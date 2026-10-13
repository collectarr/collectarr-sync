# 🔄 Collectarr Sync

Keep your Music library in step across devices, and share selected collections
on your terms. Sync is the optional self-hosted companion to Collectarr.

**Version 1 supports Music only.** Existing payload shapes and behavior become
the v1 baseline; there is no rollback to an older protocol or schema.

## ✨ Your collection, wherever you use it

- Synchronize complete personal library-entry snapshots between devices.
- Keep catalog copies and personal fields together without becoming a catalog
  provider itself.
- Isolate users and devices; handle repeated pushes and deleted entries safely.
- Publish selected collection snapshots with explicit visibility choices.
- Share a limited public view or create a revocable private sharing link.
- Keep private notes and other personal fields out unless explicitly selected.

Use [Collectarr App](https://github.com/collectarr/collectarr-app) for the library
experience and [Core](https://github.com/collectarr/collectarr-core) for canonical
Music catalog information.

## 📸 Sharing and sync

> **Screenshot placeholder — Device sync:** status and connected devices.
>
> **Screenshot placeholder — Collection sharing:** visibility and private links.

## 🧭 Independent by design

Sync is part of Collectarr's independent **clean-room implementation inspired by
CLZ collection workflows**. It is not affiliated with or endorsed by CLZ, and
includes no CLZ source code, catalog dataset or proprietary assets.

## 🔒 Predictable upgrades

Sync stores personal snapshots, not Core catalog tables. Future persistence
changes require explicit ordered migrations; supported data must survive
upgrades. A fresh baseline is for the initial v1 installation, never a shortcut
for upgrading an existing user database.

<details>
<summary>Self-hosting and development</summary>

Use Python 3.14 and follow the setup instructions in the deployment/protocol
documentation under [docs](docs/). Read [AGENTS.md](AGENTS.md) for data ownership,
isolated testing and migration requirements. Configure authentication before
exposing the service outside development.

</details>
