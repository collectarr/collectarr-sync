import pytest

from tests.conftest import bearer_headers
from tests.test_user_isolation import _owned_change


def _at(change: dict, client_changed_at: str) -> dict:
    change["changes"][0]["client_changed_at"] = client_changed_at
    return change


def _both(sync_headers: dict[str, str], user_id: str) -> dict[str, str]:
    return {**sync_headers, **bearer_headers(user_id)}


async def _conditions(client, headers: dict[str, str]) -> list[str]:
    pull = (await client.post("/sync/pull", json={}, headers=headers)).json()
    return [entity["payload"]["personal_data"]["condition"] for entity in pull["entities"]]


@pytest.mark.asyncio
async def test_health_reports_account_auth(client):
    assert (await client.get("/health")).json()["account_auth"] is True


@pytest.mark.asyncio
async def test_token_takes_precedence_over_the_shared_key(client, sync_headers):
    await client.post(
        "/sync/push",
        json=_owned_change("owned-1", "Near Mint"),
        headers=_both(sync_headers, "alice"),
    )

    assert await _conditions(client, sync_headers) == []
    assert await _conditions(client, bearer_headers("alice")) == ["Near Mint"]


@pytest.mark.asyncio
async def test_rejected_token_does_not_fall_back_to_the_shared_key(client, sync_headers):
    response = await client.post(
        "/sync/pull",
        json={},
        headers={**sync_headers, "Authorization": "Bearer not-a-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_claim_moves_the_shared_library_once(client, sync_headers):
    await client.post("/sync/push", json=_owned_change("owned-1", "Good"), headers=sync_headers)

    first = await client.post("/sync/claim-shared", headers=_both(sync_headers, "alice"))
    second = await client.post("/sync/claim-shared", headers=_both(sync_headers, "bob"))

    assert first.json() == {"entities_moved": 1}
    assert second.json() == {"entities_moved": 0}
    assert await _conditions(client, sync_headers) == []
    assert await _conditions(client, bearer_headers("alice")) == ["Good"]
    assert await _conditions(client, bearer_headers("bob")) == []


@pytest.mark.asyncio
async def test_claim_reaches_devices_whose_cursor_is_past_the_change(client, sync_headers):
    alice = bearer_headers("alice")
    await client.post("/sync/push", json=_owned_change("owned-1", "Good"), headers=sync_headers)
    cursor = (await client.post("/sync/pull", json={}, headers=alice)).json()["server_time"]

    await client.post("/sync/claim-shared", headers=_both(sync_headers, "alice"))
    pull = (await client.post("/sync/pull", json={"since": cursor}, headers=alice)).json()

    assert [entity["entity_id"] for entity in pull["entities"]] == ["owned-1"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("shared_at", "account_at", "winner"),
    [
        ("2026-02-01T10:00:00Z", "2026-01-01T10:00:00Z", "Shared"),
        ("2026-01-01T10:00:00Z", "2026-02-01T10:00:00Z", "Account"),
    ],
)
async def test_claim_keeps_the_newer_of_two_versions(
    client, sync_headers, shared_at, account_at, winner
):
    alice = bearer_headers("alice")
    await client.post(
        "/sync/push", json=_at(_owned_change("owned-1", "Shared"), shared_at), headers=sync_headers
    )
    await client.post(
        "/sync/push", json=_at(_owned_change("owned-1", "Account"), account_at), headers=alice
    )

    await client.post("/sync/claim-shared", headers=_both(sync_headers, "alice"))

    assert await _conditions(client, alice) == [winner]
    assert await _conditions(client, sync_headers) == []


@pytest.mark.asyncio
async def test_claim_requires_both_credentials(client, sync_headers):
    without_key = await client.post("/sync/claim-shared", headers=bearer_headers("alice"))
    without_token = await client.post("/sync/claim-shared", headers=sync_headers)

    assert without_key.status_code == 403
    assert without_token.status_code == 400
