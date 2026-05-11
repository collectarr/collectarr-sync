# Sync Contract

Collectarr uses an offline-first, diff-based sync model. The client writes local changes first, queues diffs, then pushes them to the server when connectivity is available.

## Concepts

- `device_id`: stable client installation identifier.
- `client_changed_at`: timestamp assigned by the client when the local mutation happened.
- `changed_at`: server timestamp assigned when the server records an accepted change.
- `entity_type`: currently `owned_item`.
- `action`: `upsert` or `delete`.
- `payload`: entity-specific data.

## Push

`POST /sync/push`

```json
{
  "device_id": "desktop-01",
  "changes": [
    {
      "entity_type": "owned_item",
      "entity_id": "3f72efaf-4a42-420c-b496-2de86302e09f",
      "device_id": "desktop-01",
      "action": "upsert",
      "client_changed_at": "2026-05-11T09:00:00Z",
      "payload": {
        "item_id": "3c7a9fd4-99c1-42f9-bf8d-4c74a7f40cda",
        "edition_id": null,
        "variant_id": null,
        "condition": "Near Mint",
        "grade": "9.4",
        "personal_notes": "Bought locally"
      }
    }
  ]
}
```

The server records accepted changes and returns the resulting server-side changes.

## Pull

`POST /sync/pull`

```json
{
  "since": "2026-05-11T08:00:00Z"
}
```

The server returns:

- `server_time`
- the user collection state, including tombstones
- ordered changes since the provided timestamp.

## Changes

`GET /sync/changes?since=2026-05-11T08:00:00Z`

Returns ordered sync change records for the authenticated user.

## Conflict Policy

The initial policy is last-write-wins:

- if the server has a newer `client_updated_at` than an incoming `client_changed_at`, the server state wins
- otherwise the incoming change is applied
- deletes are represented as tombstones so other devices can observe them.

