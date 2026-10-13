# Collection sharing

Collection sharing publishes a client-built snapshot independently of personal
sync entities. It does not query Core or refresh itself when a library entry
changes. Save in the application's Cloud Sharing page republishes the current
collection.

- `GET /sharing?kind=music` reads the authenticated owner's publication settings.
- `PUT /sharing/{collection_id}` replaces that owner's snapshot and visibility.
- `GET /public` lists public publications.
- `GET /public/{token}` renders a public or explicitly enabled private-link publication without login.

`partial` makes a collection public without personal fields. `public` allows
explicit personal-field inclusion. Both appear in the public directory.
`private` clears published items and revokes the token unless the owner enables
`private_link_enabled`. An enabled private link is excluded from the directory
and search indexing; its personal-field inclusion is independently explicit.
Republishing after revocation creates a new token. Switching between public and
private sharing also rotates the token, so a previously public URL cannot reveal
personal values subsequently included in a private publication. Updates within
the same public/private access mode retain the active token.

Snapshots have strict envelopes, unique item IDs, a 10,000-item limit, and a
5 MB serialized limit. Personal fields require explicit `include_personal`.
Image URLs accept HTTP/HTTPS only; titles and field values are HTML-escaped.
Authenticated settings and collection IDs are isolated by user. Public reads
use `no-store` so revocation does not leave a cacheable service response.

This service uses the current database baseline directly; it introduces no
legacy payload adapter or migration workflow.
