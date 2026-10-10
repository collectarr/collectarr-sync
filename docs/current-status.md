# Sync Current Status

Last reviewed: 2026-10-05.

Sync implements the personal-data v1 protocol documented in
[`protocol-contract.md`](protocol-contract.md). It stores user-partitioned
library-entry snapshots and personal entities, not Core Catalog Items or
provider data.

Library entry identity is local to the App. Payloads carry `catalog_data`,
`personal_data`, optional Core provenance, and timestamps; Sync treats the
kind-owned maps as opaque. Quantity stays inside the entry payload when the
kind uses it. Tracking, sessions, custom values, images, user folders, and
other supported personal entities use local-entry references where applicable.

The protocol retains user isolation, last-write-wins conflict handling,
tombstones, and bounded change history. Existing databases are not reset or
rewritten during implementation. A new deployment starts from an empty v1
database path. Tests remain deferred until the implementation pass is complete.
# Collection sharing

The service supports owner-isolated public collection snapshots, public Partial
visibility without personal data, and optional revocable private sharing links.
Personal field inclusion is explicit. Publications are refreshed by
the client when saving sharing settings, rather than by personal sync updates.
See [collection-sharing.md](collection-sharing.md) for endpoints and limits.

