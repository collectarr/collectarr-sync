import pytest
from conftest import bearer_headers


def snapshot(visibility="partial", include_personal=False, private_link_enabled=False):
    return {
        "title": "Music <collection>",
        "kind": "music",
        "visibility": visibility,
        "include_personal": include_personal,
        "private_link_enabled": private_link_enabled,
        "items": [
            {
                "id": "entry:1",
                "title": "Album <script>",
                "fields": {"Artist": "A & B"},
                "personal_fields": {"Notes": "Private"} if include_personal else {},
            }
        ],
    }


@pytest.mark.asyncio
async def test_unlisted_publish_revoke_and_token_rotation(client, sync_headers):
    published = await client.put(
        "/sharing/main-music",
        headers=sync_headers,
        json=snapshot("private", private_link_enabled=True),
    )
    assert published.status_code == 200
    token = published.json()["token"]
    public = await client.get(f"/public/{token}")
    assert public.status_code == 200
    assert "Album &lt;script&gt;" in public.text
    assert "A &amp; B" in public.text
    assert "Private" not in public.text
    assert public.headers["x-robots-tag"] == "noindex"
    assert token not in (await client.get("/public")).text
    await client.put("/sharing/main-music", headers=sync_headers, json=snapshot("private"))
    assert (await client.get(f"/public/{token}")).status_code == 404
    republished = await client.put(
        "/sharing/main-music", headers=sync_headers, json=snapshot("public")
    )
    assert republished.json()["token"] != token
    assert republished.json()["token"] in (await client.get("/public")).text


@pytest.mark.asyncio
async def test_sharing_is_user_isolated(client):
    a = bearer_headers("owner-a")
    b = bearer_headers("owner-b")
    first = await client.put("/sharing/same-id", headers=a, json=snapshot())
    await client.put("/sharing/same-id", headers=b, json=snapshot("private"))
    assert (await client.get(f"/public/{first.json()['token']}")).status_code == 200
    mine = await client.get("/sharing?kind=music", headers=b)
    assert len(mine.json()) == 1
    assert mine.json()[0]["visibility"] == "private"
    assert (await client.get("/sharing?kind=music")).status_code == 401
    assert (await client.put("/sharing/test", json=snapshot())).status_code == 401


@pytest.mark.asyncio
async def test_personal_fields_require_opt_in_and_snapshot_is_strict(client, sync_headers):
    data = snapshot("public", include_personal=True)
    data["include_personal"] = False
    assert (await client.put("/sharing/test", headers=sync_headers, json=data)).status_code == 422
    data["include_personal"] = True
    published = await client.put("/sharing/test", headers=sync_headers, json=data)
    assert "Private" in (await client.get(f"/public/{published.json()['token']}")).text
    data["unexpected"] = True
    assert (await client.put("/sharing/test", headers=sync_headers, json=data)).status_code == 422
    data.pop("unexpected")
    data["items"].append(data["items"][0])
    assert (await client.put("/sharing/test", headers=sync_headers, json=data)).status_code == 422


@pytest.mark.asyncio
async def test_partial_is_public_without_personal_and_private_link_rotates(client, sync_headers):
    partial = await client.put("/sharing/test", headers=sync_headers, json=snapshot())
    token = partial.json()["token"]
    assert token in (await client.get("/public")).text
    assert (await client.get(f"/public/{token}")).headers["x-robots-tag"] == "index"
    invalid = snapshot("partial", include_personal=True)
    assert (
        await client.put("/sharing/test", headers=sync_headers, json=invalid)
    ).status_code == 422
    private = await client.put(
        "/sharing/test",
        headers=sync_headers,
        json=snapshot("private", include_personal=True, private_link_enabled=True),
    )
    private_token = private.json()["token"]
    assert private_token != token
    assert (await client.get(f"/public/{token}")).status_code == 404
    assert private_token not in (await client.get("/public")).text
    assert "Private" in (await client.get(f"/public/{private_token}")).text


@pytest.mark.asyncio
async def test_unsafe_image_urls_rejected(client, sync_headers):
    data = snapshot()
    data["items"][0]["cover_url"] = "javascript:alert(1)"
    assert (await client.put("/sharing/test", headers=sync_headers, json=data)).status_code == 422
