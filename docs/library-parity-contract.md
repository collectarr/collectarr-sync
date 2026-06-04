# Library Parity Contract (Sync)

`collectarr-sync` mirrors personal collection state for the shared Collectarr
library taxonomy. Canonical metadata stays in `collectarr-core`.

- Canonical contract: https://github.com/collectarr/collectarr-core/blob/main/docs/library-parity-contract.md

## Sync-side guarantees

1. Sync payloads remain compatible with the active 9 library kinds:
   `comic`, `manga`, `anime`, `book`, `game`, `boardgame`, `movie`, `tv`, `music`.
2. Sync does not introduce alternate canonical kind mappings.
3. Sync remains personal-data-only and does not ingest provider metadata.
