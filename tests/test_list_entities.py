import base64

import pytest

CHANGED_AT = "2026-11-07T10:00:00Z"


def _change(entity_type, entity_id, payload, action="upsert"):
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "client_changed_at": CHANGED_AT,
        "payload": payload,
    }


async def _push(client, headers, *changes):
    return await client.post(
        "/sync/push",
        headers=headers,
        json={"device_id": "desktop", "changes": list(changes)},
    )


async def _pulled(client, headers):
    response = await client.post(
        "/sync/pull",
        headers=headers,
        json={"device_id": "phone", "since": None},
    )
    assert response.status_code == 200
    return {entity["entity_id"]: entity for entity in response.json()["entities"]}


def _image(size=3):
    return base64.b64encode(b"a" * size).decode()


@pytest.mark.asyncio
async def test_list_value_image_reaches_another_device(client, sync_headers):
    payload = {"list_key": "comic.custom_label", "value": "Spawn", "image": _image()}

    response = await _push(client, sync_headers, _change("list_value_image", "i1", payload))
    assert response.status_code == 200

    entity = (await _pulled(client, sync_headers))["i1"]
    assert entity["entity_type"] == "list_value_image"
    assert entity["payload"] == payload


@pytest.mark.asyncio
async def test_list_value_image_delete_needs_no_image(client, sync_headers):
    response = await _push(
        client,
        sync_headers,
        _change(
            "list_value_image",
            "i1",
            {"list_key": "comic.custom_label", "value": "Spawn"},
            action="delete",
        ),
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "image",
    [_image(2 * 1024 * 1024) + "AAAA", "@@@"],
    ids=["above the limit", "not base64"],
)
@pytest.mark.asyncio
async def test_list_value_image_refuses_a_bad_image(client, sync_headers, image):
    response = await _push(
        client,
        sync_headers,
        _change("list_value_image", "i1", {"list_key": "l", "value": "v", "image": image}),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_value_image_accepts_the_largest_image(client, sync_headers):
    payload = {"list_key": "l", "value": "v", "image": _image(2 * 1024 * 1024)}

    response = await _push(client, sync_headers, _change("list_value_image", "i1", payload))

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_custom_field_definition_reaches_another_device(client, sync_headers):
    payload = {
        "name": "Signed by",
        "field_type": "text",
        "media_kind": "comic",
        "sort_order": 2,
        "created_at": CHANGED_AT,
    }

    response = await _push(
        client, sync_headers, _change("custom_field_definition", "f1", payload)
    )
    assert response.status_code == 200

    pulled = (await _pulled(client, sync_headers))["f1"]["payload"]
    assert pulled["name"] == "Signed by"
    assert pulled["media_kind"] == "comic"
    assert pulled["sort_order"] == 2


@pytest.mark.asyncio
async def test_custom_field_definition_delete_needs_no_payload(client, sync_headers):
    response = await _push(
        client,
        sync_headers,
        _change("custom_field_definition", "f1", {}, action="delete"),
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "kind",
    ["music", "comic", "book", "game", "game_hardware", "game_toy", "boardgame", "movie"],
)
@pytest.mark.asyncio
async def test_every_library_kind_syncs(client, sync_headers, kind):
    payload = {
        "kind": kind,
        "catalog_data": {"title": "Example"},
        "personal_data": {},
        "updated_at": CHANGED_AT,
    }

    response = await _push(client, sync_headers, _change("library_entry", "e1", payload))

    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_pick_list_value_keeps_its_details(client, sync_headers):
    payload = {
        "list_name": "borrower",
        "value": "Alex Example",
        "sort_order": 0,
        "sort_name": "Example, Alex",
        "is_hidden": True,
        "email": "alex@example.invalid",
        "address": "1 Example Street",
    }

    response = await _push(client, sync_headers, _change("pick_list_value", "b1", payload))
    assert response.status_code == 200

    assert (await _pulled(client, sync_headers))["b1"]["payload"] == payload
