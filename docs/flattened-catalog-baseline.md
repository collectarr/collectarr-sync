# Flattened Catalog Baseline (Sync)

This work starts from the following clean Sync revision:

| Repository | Branch | Baseline commit |
|---|---|---|
| Sync | `codex/pre-cutover-rollback-20260929` | `625d82cbb7c1c11fc2f112bde4f3510811096b59` |
| App | `codex/pre-cutover-rollback-20260929` | `6949fb4f00e6fdd5828e21474b74fa448e793fe9` |

## Current protocol surfaces to replace

The existing protocol accepts personal entity payloads including `owned_item`, `tracking_entry`, `wishlist_item`, `note`, `watch_session`, `metadata_override`, `custom_episode`, and `pick_list_value`. It also accepts `library_item_snapshot`, which duplicates catalog metadata into Sync. Owned and wishlist payloads can encode legacy `anchor_type`, edition, variant, and bundle-release coordinates.

The flattened target protocol must sync App-owned personal state only. Canonical catalog items and their genuine catalog children remain in Core. Personal entity identity must use explicit catalog-item or owned-item references; old Work/Release/Copy anchors and catalog snapshots are removed from the final protocol. Existing user isolation, entity-scoped identity, last-write-wins conflict handling, and tombstones must remain intact.

## Cutover safety

- Keep the current service available while the App and Sync payloads are being moved together.
- Replace the accepted entity set and documentation as one coordinated protocol change; do not silently normalize old anchors into a guessed item.
- Keep Sync databases and deployed services untouched during implementation. The final v1 setup instructions must describe a fresh database and explicitly state that old payload/database formats are unsupported.
