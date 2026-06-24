"""Multi-user isolation tests.

These guard against the regression where personal sync state was keyed only by
``(entity_type, entity_id)``, letting one user silently overwrite, read, or
delete another user's data on a shared sync instance.
"""

import pytest

from tests.conftest import bearer_headers


def _owned_change(entity_id: str, condition: str) -> dict:
    return {
        "device_id": "device-1",
        "changes": [
            {
                "entity_type": "owned_item",
                "entity_id": entity_id,
                "action": "upsert",
                "client_changed_at": "2026-01-15T10:00:00Z",
                "payload": {"item_id": "comic-1", "condition": condition},
            }
        ],
    }


@pytest.mark.asyncio
async def test_users_do_not_overwrite_each_other(client):
    alice = bearer_headers("alice")
    bob = bearer_headers("bob")

    # Both users push the SAME entity_id with different payloads.
    r1 = await client.post("/sync/push", json=_owned_change("owned-1", "Near Mint"), headers=alice)
    r2 = await client.post("/sync/push", json=_owned_change("owned-1", "Good"), headers=bob)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(r1.json()["accepted"]) == 1
    assert len(r2.json()["accepted"]) == 1

    # Each user pulls only their own version; no cross-user overwrite.
    alice_pull = (await client.post("/sync/pull", json={}, headers=alice)).json()
    bob_pull = (await client.post("/sync/pull", json={}, headers=bob)).json()

    assert len(alice_pull["entities"]) == 1
    assert len(bob_pull["entities"]) == 1
    assert alice_pull["entities"][0]["payload"]["condition"] == "Near Mint"
    assert bob_pull["entities"][0]["payload"]["condition"] == "Good"


@pytest.mark.asyncio
async def test_status_is_scoped_per_user(client):
    alice = bearer_headers("alice")
    bob = bearer_headers("bob")

    await client.post("/sync/push", json=_owned_change("owned-1", "Near Mint"), headers=alice)
    await client.post("/sync/push", json=_owned_change("owned-2", "Good"), headers=alice)
    await client.post("/sync/push", json=_owned_change("owned-9", "Fair"), headers=bob)

    alice_status = (await client.get("/sync/status", headers=alice)).json()
    bob_status = (await client.get("/sync/status", headers=bob)).json()

    assert alice_status["entity_count"] == 2
    assert bob_status["entity_count"] == 1


@pytest.mark.asyncio
async def test_devices_are_scoped_per_user(client):
    alice = bearer_headers("alice")
    bob = bearer_headers("bob")

    await client.post("/sync/push", json=_owned_change("owned-1", "Near Mint"), headers=alice)
    await client.post("/sync/push", json=_owned_change("owned-9", "Fair"), headers=bob)

    alice_devices = (await client.get("/sync/devices", headers=alice)).json()
    assert {d["device_id"] for d in alice_devices} == {"device-1"}
    assert alice_devices[0]["change_count"] == 1


@pytest.mark.asyncio
async def test_user_cannot_delete_another_users_device_history(client):
    alice = bearer_headers("alice")
    bob = bearer_headers("bob")

    await client.post("/sync/push", json=_owned_change("owned-1", "Near Mint"), headers=alice)

    # Bob tries to remove "device-1" which only belongs to Alice.
    bob_delete = await client.delete("/sync/devices/device-1", headers=bob)
    assert bob_delete.status_code == 404

    # Alice's data is untouched.
    alice_status = (await client.get("/sync/status", headers=alice)).json()
    assert alice_status["entity_count"] == 1


@pytest.mark.asyncio
async def test_missing_auth_is_rejected(client):
    resp = await client.post("/sync/push", json=_owned_change("owned-1", "Near Mint"))
    assert resp.status_code == 401
