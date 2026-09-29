# Flattened Catalog Baseline (Sync)

This work starts from the following clean Sync revision:

| Repository | Branch | Baseline commit |
|---|---|---|
| Sync | `codex/pre-cutover-rollback-20260929` | `625d82cbb7c1c11fc2f112bde4f3510811096b59` |
| App | `codex/pre-cutover-rollback-20260929` | `6949fb4f00e6fdd5828e21474b74fa448e793fe9` |

## Pre-cutover protocol recorded for migration context

At the recorded baseline, the protocol accepted `owned_item`, `tracking_entry`, `wishlist_item`, `note`, `watch_session`, `metadata_override`, `custom_episode`, and `pick_list_value`. It also accepted `library_item_snapshot`, which duplicated catalog metadata into Sync. Owned and wishlist payloads could encode legacy `anchor_type`, edition, variant, and bundle-release coordinates. These details describe the migration source only; the supported v1 set and payloads are defined in `protocol-contract.md`.

The flattened protocol syncs App-owned personal state only. Canonical Catalog Items and their genuine catalog children remain in Core. Personal entity identity uses explicit catalog-item or owned-item references; old Work/Release/Copy anchors and catalog snapshots are rejected by the v1 contract. Existing user isolation, entity-scoped identity, last-write-wins conflict handling, and tombstones remain required.

## Cutover safety

- Keep the current service available while the App and Sync payloads are being moved together.
- Replace the accepted entity set and documentation as one coordinated protocol change; do not silently normalize old anchors into a guessed item.
- Keep Sync databases and deployed services untouched during implementation. The final v1 setup instructions must describe a fresh database and explicitly state that old payload/database formats are unsupported.
