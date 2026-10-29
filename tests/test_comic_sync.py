import pytest


@pytest.mark.asyncio
async def test_comic_snapshot_preserves_catalog_and_personal_data(client, sync_headers):
    catalog = {
        "title": "Issue title", "series_title": "Series", "issue_number": "1/2",
        "variant": "B", "variant_description": "Foil", "subtitle": "Issue subtitle",
        "publication_age": "Modern", "age_rating": "Teen",
        "cover_date": {"year": 2024}, "release_date_parts": {"month": 5, "day": 3},
        "creators": [{"name": "Example Writer", "role": "Writer"}],
    }
    personal = {
        "grade": "9.8", "condition": "Near Mint", "quantity": 2,
        "details": {"raw_or_slabbed": "Slabbed", "grading_company": "CGC",
                    "certification_number": "123", "key_comic": True,
                    "key_severity": "Major", "last_bag_board_date": "2026-01-02"},
    }
    response = await client.post('/sync/push', headers=sync_headers, json={
        'device_id': 'desktop', 'changes': [{
            'entity_type': 'library_entry', 'entity_id': 'owned-comic', 'action': 'upsert',
            'client_changed_at': '2026-10-29T10:00:00Z',
            'payload': {'kind': 'comic', 'catalog_data': catalog, 'personal_data': personal,
                        'source_catalog_ref': {'kind': 'comic', 'id': 'issue-1'},
                        'updated_at': '2026-10-29T10:00:00Z'},
        }],
    })
    assert response.status_code == 200, response.text
    assert len(response.json()['accepted']) == 1
    pull = await client.post('/sync/pull', headers=sync_headers, json={})
    assert pull.status_code == 200
    payload = pull.json()['entities'][0]['payload']
    assert payload['kind'] == 'comic'
    assert payload['catalog_data'] == catalog
    assert payload['personal_data'] == personal
