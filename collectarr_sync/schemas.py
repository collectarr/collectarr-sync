from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SyncAction = Literal["upsert", "delete"]
SYNC_PROTOCOL_VERSION = 1


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class TrackingEntryPayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=120)
    owned_item_id: str | None = Field(default=None, min_length=1, max_length=120)
    edition_id: str | None = Field(default=None, min_length=1, max_length=120)
    variant_id: str | None = Field(default=None, min_length=1, max_length=120)
    source_type: str | None = Field(default=None, min_length=1, max_length=64)
    status: str | None = Field(default=None, min_length=1, max_length=64)
    rating: int | None = Field(default=None, ge=0, le=10)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress_current: int | None = Field(default=None, ge=0)
    progress_total: int | None = Field(default=None, ge=0)
    times_completed: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=4000)
    season_number: int | None = Field(default=None, ge=0)
    episode_number: int | None = Field(default=None, ge=0)

    @field_validator("started_at", "finished_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None

    @field_validator("progress_total")
    @classmethod
    def validate_progress_total(cls, value: int | None) -> int | None:
        if value == 0:
            raise ValueError("progress_total must be greater than 0 when provided")
        return value

    @field_validator("finished_at")
    @classmethod
    def validate_finished_at(cls, value: datetime | None, info) -> datetime | None:
        started_at = info.data.get("started_at")
        if value and started_at and value < started_at:
            raise ValueError("finished_at must not be earlier than started_at")
        return value

    @field_validator("progress_current")
    @classmethod
    def validate_progress_current(cls, value: int | None, info) -> int | None:
        progress_total = info.data.get("progress_total")
        if value is not None and progress_total is not None and value > progress_total:
            raise ValueError("progress_current must not exceed progress_total")
        return value


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

    @field_validator("payload")
    @classmethod
    def validate_payload_for_entity_type(cls, value: dict[str, Any], info) -> dict[str, Any]:
        entity_type = info.data.get("entity_type")
        if entity_type == "tracking_entry":
            return TrackingEntryPayload.model_validate(value).model_dump(exclude_none=True)
        return value


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
    current_action: SyncAction | None = None
    current_payload: dict[str, Any] | None = None


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
    protocol_version: int
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
