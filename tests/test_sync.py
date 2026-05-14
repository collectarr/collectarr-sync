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
async def test_push_then_pull_returns_library_item_snapshot(client, sync_headers):
    response = await client.post(
        "/sync/push",
        headers=sync_headers,
        json={
            "device_id": "desktop",
            "changes": [
                {
                    "entity_type": "library_item_snapshot",
                    "entity_id": "comic-1",
                    "action": "upsert",
                    "client_changed_at": "2026-05-11T10:00:00Z",
                    "payload": {
                        "snapshot_version": 1,
                        "kind": "comic",
                        "title": "Absolute Batman",
                        "item_number": "1",
                        "cover_image_url": "https://cdn.example/absolute.jpg",
                    },
                }
            ],
        },
    )

    pull = await client.post("/sync/pull", headers=sync_headers, json={})

    assert response.status_code == 200
    assert pull.status_code == 200
    entity = pull.json()["entities"][0]
    assert entity["entity_type"] == "library_item_snapshot"
    assert entity["entity_id"] == "comic-1"
    assert entity["payload"]["title"] == "Absolute Batman"


@pytest.mark.asyncio
async def test_sync_status_reports_counts(client, sync_headers):
    unauthorized = await client.get("/sync/status")
    assert unauthorized.status_code == 401

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
                    "client_changed_at": "2026-05-11T10:00:00Z",
                    "payload": {"item_id": "comic-1"},
                }
            ],
        },
    )

    response = await client.get("/sync/status", headers=sync_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == 1
    assert data["entity_count"] == 1
    assert data["tombstone_count"] == 0
    assert data["change_count"] == 1
    assert data["retention_days"] == 90
    assert data["last_changed_at"] is not None


@pytest.mark.asyncio
async def test_sync_devices_reports_seen_devices(client, sync_headers):
    for device_id, entity_type, entity_id in [
        ("desktop", "owned_item", "comic-1"),
        ("phone", "wishlist_item", "comic-2"),
    ]:
        await client.post(
            "/sync/push",
            headers=sync_headers,
            json={
                "device_id": device_id,
                "changes": [
                    {
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "action": "upsert",
                        "client_changed_at": "2026-05-12T08:00:00Z",
                        "payload": {"item_id": entity_id},
                    }
                ],
            },
        )

    unauthorized = await client.get("/sync/devices")
    assert unauthorized.status_code == 401

    response = await client.get("/sync/devices", headers=sync_headers)

    assert response.status_code == 200
    devices = {item["device_id"]: item for item in response.json()}
    assert set(devices) == {"desktop", "phone"}
    assert devices["desktop"]["change_count"] == 1
    assert devices["desktop"]["first_seen_at"] is not None
    assert devices["desktop"]["last_seen_at"] is not None


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


@pytest.mark.asyncio
async def test_pull_prunes_old_change_log_entries(client, sync_headers):
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
        "/sync/pull",
        headers=sync_headers,
        json={"since": "1999-01-01T00:00:00Z"},
    )
    changes = await client.get(
        "/sync/changes",
        headers=sync_headers,
        params={"since": "1999-01-01T00:00:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["changes"] == []
    assert changes.json()["changes"] == []
