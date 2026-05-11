from datetime import UTC, datetime

import pytest

from collectarr_sync.db import connect


@pytest.mark.asyncio
async def test_push_requires_sync_key(client):
    response = await client.post("/sync/push", json={"device_id": "desktop", "changes": []})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_push_then_pull_returns_personal_entity(client, sync_headers):
    response = await client.post(
        "/sync/push",
        headers=sync_headers,
        json={
            "device_id": "desktop",
            "changes": [
                {
                    "entity_type": "owned_item",
                    "entity_id": "owned-1",
                    "action": "upsert",
                    "client_changed_at": "2026-05-11T10:00:00Z",
                    "payload": {
                        "item_id": "comic-1",
                        "condition": "Near Mint",
                        "grade": "9.8",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    assert len(response.json()["accepted"]) == 1

    pull = await client.post("/sync/pull", headers=sync_headers, json={})

    assert pull.status_code == 200
    data = pull.json()
    assert data["entities"][0]["entity_id"] == "owned-1"
    assert data["entities"][0]["payload"]["grade"] == "9.8"
    assert data["changes"] == []

    incremental = await client.post(
        "/sync/pull",
        headers=sync_headers,
        json={"since": "2026-05-11T00:00:00Z"},
    )
    assert incremental.json()["changes"][0]["device_id"] == "desktop"


@pytest.mark.asyncio
async def test_stale_client_change_is_rejected(client, sync_headers):
    await client.post(
        "/sync/push",
        headers=sync_headers,
        json={
            "device_id": "desktop",
            "changes": [
                {
                    "entity_type": "owned_item",
                    "entity_id": "owned-1",
                    "action": "upsert",
                    "client_changed_at": "2026-05-11T12:00:00Z",
                    "payload": {"grade": "9.8"},
                }
            ],
        },
    )

    response = await client.post(
        "/sync/push",
        headers=sync_headers,
        json={
            "device_id": "android",
            "changes": [
                {
                    "entity_type": "owned_item",
                    "entity_id": "owned-1",
                    "action": "upsert",
                    "client_changed_at": "2026-05-11T11:00:00Z",
                    "payload": {"grade": "9.4"},
                }
            ],
        },
    )

    data = response.json()
    assert response.status_code == 200
    assert data["accepted"] == []
    assert data["rejected"][0]["reason"] == "server_has_newer_client_change"


@pytest.mark.asyncio
async def test_delete_is_returned_as_tombstone(client, sync_headers):
    response = await client.post(
        "/sync/push",
        headers=sync_headers,
        json={
            "device_id": "desktop",
            "changes": [
                {
                    "entity_type": "wishlist_item",
                    "entity_id": "wish-1",
                    "action": "delete",
                    "client_changed_at": "2026-05-11T10:00:00Z",
                    "payload": {},
                }
            ],
        },
    )
    changed_at = response.json()["accepted"][0]["changed_at"]

    changes = await client.get(
        "/sync/changes",
        headers=sync_headers,
        params={"since": datetime(2026, 5, 11, tzinfo=UTC).isoformat()},
    )
    pull = await client.post(
        "/sync/pull",
        headers=sync_headers,
        json={"since": "2026-05-11T00:00:00Z"},
    )

    assert changes.status_code == 200
    assert changes.json()["changes"][0]["action"] == "delete"
    assert pull.json()["entities"][0]["deleted_at"] == changed_at


@pytest.mark.asyncio
async def test_push_prunes_old_change_log_entries(client, sync_headers):
    connection = await connect()
    try:
        await connection.execute(
            """
            insert into changes (
              id, entity_type, entity_id, action, payload_json, device_id,
              client_changed_at, changed_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "old-change",
                "owned_item",
                "owned-old",
                "upsert",
                "{}",
                "desktop",
                "2000-01-01T00:00:00Z",
                "2000-01-01T00:00:00Z",
            ),
        )
        await connection.commit()
    finally:
        await connection.close()

    response = await client.post(
        "/sync/push",
        headers=sync_headers,
        json={"device_id": "desktop", "changes": []},
    )
    changes = await client.get(
        "/sync/changes",
        headers=sync_headers,
        params={"since": "1999-01-01T00:00:00Z"},
    )

    assert response.status_code == 200
    assert changes.json()["changes"] == []
