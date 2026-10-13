"""Published collection snapshots, isolated from personal sync records."""

import json
import secrets
from html import escape
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from collectarr_sync.db import connect


class ShareItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=1000)
    subtitle: str | None = Field(default=None, max_length=1000)
    cover_url: HttpUrl | None = None
    fields: dict[str, str] = Field(default_factory=dict, max_length=200)
    personal_fields: dict[str, str] = Field(default_factory=dict, max_length=200)


class SharePublication(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=200)
    kind: Literal["music", "book", "comic", "manga", "movie", "tv", "anime", "game", "boardgame"]
    visibility: Literal["private", "partial", "public"]
    private_link_enabled: bool = False
    include_personal: bool = False
    items: list[ShareItem] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def validate_snapshot(self):
        if self.visibility == "partial" and self.include_personal:
            raise ValueError("Partial sharing excludes personal fields")
        if self.visibility != "private" and self.private_link_enabled:
            raise ValueError("Private sharing links require private visibility")
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Share item IDs must be unique")
        if not self.include_personal and any(item.personal_fields for item in self.items):
            raise ValueError("Personal fields require explicit inclusion")
        if len(self.model_dump_json().encode()) > 5_000_000:
            raise ValueError("Share snapshot exceeds 5 MB")
        return self


async def publish(user_id: str, collection_id: str, snapshot: SharePublication) -> dict:
    db = await connect()
    try:
        cursor = await db.execute(
            "select token, visibility from collection_shares where user_id = ? and collection_id = ?",
            (user_id, collection_id),
        )
        existing = await cursor.fetchone()
        inaccessible = snapshot.visibility == "private" and not snapshot.private_link_enabled
        reuse_token = (
            existing
            and existing["token"]
            and (existing["visibility"] == "private") == (snapshot.visibility == "private")
        )
        token = (
            None
            if inaccessible
            else (existing["token"] if reuse_token else secrets.token_urlsafe(24))
        )
        data = snapshot.model_dump(mode="json")
        if inaccessible:
            data["items"] = []
        await db.execute(
            """insert into collection_shares (user_id, collection_id, token, visibility, payload_json)
            values (?, ?, ?, ?, ?) on conflict (user_id, collection_id) do update set
            token = excluded.token, visibility = excluded.visibility, payload_json = excluded.payload_json""",
            (user_id, collection_id, token, snapshot.visibility, json.dumps(data)),
        )
        await db.commit()
        return {"collection_id": collection_id, "token": token, **data}
    finally:
        await db.close()


async def settings_for(user_id: str, kind: str) -> list[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "select collection_id, token, payload_json from collection_shares where user_id = ?",
            (user_id,),
        )
        result = []
        for row in await cursor.fetchall():
            data = json.loads(row["payload_json"])
            if data["kind"] == kind:
                result.append(
                    {"collection_id": row["collection_id"], "token": row["token"], **data}
                )
        return result
    finally:
        await db.close()


async def public_snapshot(token: str) -> dict:
    db = await connect()
    try:
        cursor = await db.execute(
            "select payload_json from collection_shares where token = ?",
            (token,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(404, "Collection is private or no longer shared")
        return json.loads(row["payload_json"])
    finally:
        await db.close()


async def public_collections() -> list[dict]:
    db = await connect()
    try:
        cursor = await db.execute(
            "select token, payload_json from collection_shares where visibility in ('partial', 'public')"
        )
        return [
            {"token": row["token"], "title": json.loads(row["payload_json"])["title"]}
            for row in await cursor.fetchall()
        ]
    finally:
        await db.close()


def render_collection(data: dict) -> str:
    rows = []
    for item in data["items"]:
        fields = {**item["fields"], **item["personal_fields"]}
        details = "".join(
            f"<dt>{escape(key)}</dt><dd>{escape(value)}</dd>" for key, value in fields.items()
        )
        cover = (
            f'<img src="{escape(item["cover_url"], quote=True)}" alt="" loading="lazy">'
            if item.get("cover_url")
            else ""
        )
        rows.append(
            f"<article>{cover}<h2>{escape(item['title'])}</h2>"
            f"<p>{escape(item.get('subtitle') or '')}</p><dl>{details}</dl></article>"
        )
    return page(data["title"], "".join(rows))


def page(title: str, body: str) -> str:
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title><style>"
        "body{background:#131313;color:#eee;font:14px system-ui;margin:24px}"
        "main{max-width:1200px;margin:auto}article{background:#383838;padding:16px;margin:12px 0}"
        "img{width:120px;float:right}dt{font-weight:700}dd{margin:0 0 8px}a{color:#f2932f}"
        f"</style></head><body><main><h1>{escape(title)}</h1>{body}</main></body></html>"
    )
