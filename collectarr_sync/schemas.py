from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SyncAction = Literal["upsert", "delete"]


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class SyncChangeIn(BaseModel):
    entity_type: str = Field(min_length=1, max_length=80)
    entity_id: str = Field(min_length=1, max_length=120)
    action: SyncAction
    client_changed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("client_changed_at")
    @classmethod
    def normalize_client_changed_at(cls, value: datetime) -> datetime:
        return as_utc(value)


class SyncPushRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=120)
    changes: list[SyncChangeIn]


class SyncChangeOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: SyncAction
    device_id: str
    client_changed_at: datetime
    changed_at: datetime
    payload: dict[str, Any]


class RejectedChange(BaseModel):
    entity_type: str
    entity_id: str
    reason: str
    current_client_changed_at: datetime | None = None


class SyncPushResponse(BaseModel):
    server_time: datetime
    accepted: list[SyncChangeOut]
    rejected: list[RejectedChange]


class SyncPullRequest(BaseModel):
    since: datetime | None = None

    @field_validator("since")
    @classmethod
    def normalize_since(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class SyncedEntity(BaseModel):
    entity_type: str
    entity_id: str
    action: SyncAction
    source_device_id: str
    client_changed_at: datetime
    changed_at: datetime
    deleted_at: datetime | None = None
    payload: dict[str, Any]


class SyncPullResponse(BaseModel):
    server_time: datetime
    entities: list[SyncedEntity]
    changes: list[SyncChangeOut]


class SyncChangesResponse(BaseModel):
    server_time: datetime
    changes: list[SyncChangeOut]


class SyncStatusResponse(BaseModel):
    server_time: datetime
    schema_version: int
    entity_count: int
    tombstone_count: int
    change_count: int
    retention_days: int
    last_changed_at: datetime | None = None


class SyncDeviceResponse(BaseModel):
    device_id: str
    change_count: int
    first_seen_at: datetime
    last_seen_at: datetime
