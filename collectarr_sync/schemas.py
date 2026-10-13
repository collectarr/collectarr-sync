from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SyncAction = Literal["upsert", "delete"]
TrackingSourceType = Literal["physical", "digital", "streaming"]
MediaKind = Literal["music"]
SyncEntityType = Literal[
    "library_entry",
    "wishlist_item",
    "tracking_entry",
    "music_listen_event",
    "metadata_override",
    "location",
    "user_folder",
    "pick_list_value",
]
SYNC_PROTOCOL_VERSION = 1


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _reject_nested_target(value: Any) -> Any:
    if isinstance(value, dict) and "target_ref" in value:
        raise ValueError("target_ref is not part of the Catalog Item v1 protocol")
    return value


class CatalogItemRefPayload(BaseModel):
    kind: MediaKind
    id: str = Field(min_length=1, max_length=120)

    model_config = {"extra": "forbid"}


class LibraryEntryRefPayload(BaseModel):
    kind: MediaKind
    id: str = Field(min_length=1, max_length=120)

    model_config = {"extra": "forbid"}


class TrackingEntryPayload(BaseModel):
    library_entry_ref: LibraryEntryRefPayload
    source_type: TrackingSourceType | None = None
    status: str | None = Field(default=None, min_length=1, max_length=64)
    rating: int | None = Field(default=None, ge=0, le=10)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress_total: int | None = Field(default=None, ge=0)
    progress_current: int | None = Field(default=None, ge=0)
    times_completed: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=4000)

    # Kind-owned tracking codecs may add fields such as pages, chapters, or
    # issue coordinates; the shared service does not interpret those values.
    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def reject_nested_target(cls, value: Any) -> Any:
        if isinstance(value, dict) and "catalog_ref" in value:
            raise ValueError("tracking entries use library_entry_ref only")
        return _reject_nested_target(value)

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


class LibraryEntryPayload(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=120)
    kind: MediaKind
    catalog_data: dict[str, Any]
    personal_data: dict[str, Any]
    source_catalog_ref: CatalogItemRefPayload | None = None
    created_at: datetime | None = None
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def reject_nested_target(cls, value: Any) -> Any:
        return _reject_nested_target(value)

    @model_validator(mode="after")
    def validate_source_kind(self):
        if self.source_catalog_ref is not None and self.source_catalog_ref.kind != self.kind:
            raise ValueError("source_catalog_ref kind must match library entry kind")
        return self

    @field_validator("created_at", "updated_at", "deleted_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class WishlistItemPayload(BaseModel):
    catalog_ref: CatalogItemRefPayload
    target_price_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=16)
    notes: str | None = Field(default=None, max_length=4000)
    created_at: datetime | None = None

    model_config = {"extra": "forbid"}

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class WatchSessionPayload(BaseModel):
    library_entry_ref: LibraryEntryRefPayload
    tracking_entry_id: str | None = Field(default=None, min_length=1, max_length=120)
    season_number: int | None = Field(default=None, ge=0)
    episode_number: int | None = Field(default=None, ge=0)
    source_type: TrackingSourceType | None = None
    watched_at: datetime
    seen_where: str | None = Field(default=None, max_length=255)
    rating: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=4000)

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def reject_nested_target(cls, value: Any) -> Any:
        return _reject_nested_target(value)

    @field_validator("watched_at")
    @classmethod
    def normalize_watched_at(cls, value: datetime) -> datetime:
        return as_utc(value)

    @model_validator(mode="after")
    def validate_owned_entry_kind(self):
        if self.library_entry_ref.kind not in {"anime", "tv"}:
            raise ValueError("watch sessions require an Anime or TV library entry")
        return self


class MusicListenEventPayload(BaseModel):
    library_entry_ref: LibraryEntryRefPayload
    listened_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=4000)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_library_entry_kind(self):
        if self.library_entry_ref.kind != "music":
            raise ValueError("music listen events require a Music library entry")
        if self.finished_at and self.started_at and self.finished_at < self.started_at:
            raise ValueError("finished_at must not be earlier than started_at")
        return self

    @field_validator(
        "listened_at",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    @classmethod
    def normalize_event_datetimes(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        return as_utc(value) if value else None


class MetadataOverridePayload(BaseModel):
    library_entry_ref: LibraryEntryRefPayload
    field_key: str = Field(min_length=1, max_length=255)
    original_value: str | None = Field(default=None, max_length=8000)
    override_value: str = Field(min_length=0, max_length=8000)

    model_config = {"extra": "forbid"}


class CustomEpisodePayload(BaseModel):
    library_entry_ref: LibraryEntryRefPayload
    season_number: int = Field(ge=0, le=9999)
    episode_number: int = Field(ge=0, le=99999)
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=8000)
    air_date: str | None = Field(default=None, max_length=30)
    runtime_minutes: int | None = Field(default=None, ge=0, le=99999)
    still_image_url: str | None = Field(default=None, max_length=2048)
    local_image_path: str | None = Field(default=None, max_length=4096)
    thumbnail_image_url: str | None = Field(default=None, max_length=2048)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_entry_kind(self) -> CustomEpisodePayload:
        if self.library_entry_ref.kind not in {"anime", "tv"}:
            raise ValueError("custom episodes require an Anime or TV library entry")
        return self


class PickListValuePayload(BaseModel):
    list_name: str = Field(min_length=1, max_length=120)
    media_kind: str | None = Field(default=None, max_length=64)
    value: str = Field(min_length=1, max_length=500)
    sort_order: int = Field(default=0, ge=0)


class LocationPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0)


class UserFolderPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    parent_id: str | None = Field(default=None, min_length=1, max_length=120)
    icon_name: str | None = Field(default=None, max_length=120)
    sort_order: int = Field(default=0, ge=0)


class TrackingUnitPayload(BaseModel):
    library_entry_ref: LibraryEntryRefPayload
    tracking_entry_id: str | None = Field(default=None, min_length=1, max_length=120)
    completed_at: datetime

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def reject_nested_target(cls, value: Any) -> Any:
        if isinstance(value, dict) and "catalog_ref" in value:
            raise ValueError("tracking units use library_entry_ref only")
        return _reject_nested_target(value)

    @field_validator("completed_at")
    @classmethod
    def normalize_completed_at(cls, value: datetime) -> datetime:
        return as_utc(value)



class SyncChangeIn(BaseModel):
    entity_type: SyncEntityType
    entity_id: str = Field(min_length=1, max_length=120)
    action: SyncAction
    client_change_id: str | None = Field(default=None, min_length=1, max_length=120)
    client_changed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("client_changed_at")
    @classmethod
    def normalize_client_changed_at(cls, value: datetime) -> datetime:
        return as_utc(value)

    @field_validator("payload")
    @classmethod
    def validate_payload_for_entity_type(
        cls,
        value: dict[str, Any],
        info,
    ) -> dict[str, Any]:
        entity_type = info.data.get("entity_type")
        action = info.data.get("action")
        if (
            action == "delete"
            and entity_type != "library_entry"
            and entity_type != "music_listen_event"
            and not value
        ):
            return value
        if entity_type == "music_listen_event":
            return MusicListenEventPayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "tracking_entry":
            return TrackingEntryPayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "metadata_override":
            return MetadataOverridePayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "library_entry":
            payload = LibraryEntryPayload.model_validate(value)
            if payload.id is not None and payload.id != info.data.get("entity_id"):
                raise ValueError("library_entry payload id must match entity_id")
            return payload.model_dump(mode="json", exclude_none=True)
        if entity_type == "wishlist_item":
            return WishlistItemPayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "tracking_unit":
            return TrackingUnitPayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "watch_session":
            return WatchSessionPayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "custom_episode":
            return CustomEpisodePayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "pick_list_value":
            return PickListValuePayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "location":
            return LocationPayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
        if entity_type == "user_folder":
            return UserFolderPayload.model_validate(value).model_dump(
                mode="json", exclude_none=True
            )
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
