from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SyncAction = Literal["upsert", "delete"]
TrackingSourceType = Literal["physical", "digital", "streaming"]
PersonalAnchorType = Literal["item", "edition", "variant", "bundle_release"]
SYNC_PROTOCOL_VERSION = 1


def _has_anchor_value(value: str | None) -> bool:
    trimmed = value.strip() if value else ""
    return bool(trimmed)


def normalize_personal_anchor_type(value: str | None) -> PersonalAnchorType | None:
    normalized = value.strip().lower() if isinstance(value, str) else None
    if not normalized:
        return None
    if normalized in {"item", "media", "work"}:
        return "item"
    if normalized in {"edition", "release"}:
        return "edition"
    if normalized in {"variant", "physical_release", "physical-release"}:
        return "variant"
    if normalized in {
        "bundle_release",
        "bundle-release",
        "bundle",
        "package",
        "box_set",
        "box-set",
    }:
        return "bundle_release"
    raise ValueError(f"Unsupported personal anchor type: {value}")


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class TrackingEntryPayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=120)
    owned_item_id: str | None = Field(default=None, min_length=1, max_length=120)
    edition_id: str | None = Field(default=None, min_length=1, max_length=120)
    variant_id: str | None = Field(default=None, min_length=1, max_length=120)
    source_type: TrackingSourceType | None = None
    status: str | None = Field(default=None, min_length=1, max_length=64)
    rating: int | None = Field(default=None, ge=0, le=10)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress_total: int | None = Field(default=None, ge=0)
    progress_current: int | None = Field(default=None, ge=0)
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


class _PersonalEntityPayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=120)
    anchor_type: PersonalAnchorType | None = None
    edition_id: str | None = Field(default=None, min_length=1, max_length=120)
    variant_id: str | None = Field(default=None, min_length=1, max_length=120)
    bundle_release_id: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("anchor_type", mode="before")
    @classmethod
    def normalize_anchor_type(cls, value: str | None) -> PersonalAnchorType | None:
        return normalize_personal_anchor_type(value)

    @model_validator(mode="after")
    def validate_anchor_fields(self) -> "_PersonalEntityPayload":
        has_edition = _has_anchor_value(self.edition_id)
        has_variant = _has_anchor_value(self.variant_id)
        has_bundle_release = _has_anchor_value(self.bundle_release_id)

        if has_bundle_release:
            if self.anchor_type not in (None, "bundle_release"):
                raise ValueError(
                    "bundle_release_id requires anchor_type 'bundle_release'"
                )
            self.anchor_type = "bundle_release"
        if self.anchor_type == "bundle_release" and not self.bundle_release_id:
            raise ValueError(
                "bundle_release_id is required when anchor_type is 'bundle_release'"
            )

        if has_variant:
            self.anchor_type = "variant"
            return self

        if has_edition:
            if self.anchor_type not in (None, "edition", "variant"):
                raise ValueError(
                    "edition_id is only compatible with anchor_type 'edition' or 'variant'"
                )
            self.anchor_type = "edition"
            return self

        if self.anchor_type == "edition":
            raise ValueError("edition_id is required when anchor_type is 'edition'")
        if self.anchor_type == "variant":
            raise ValueError(
                "variant_id or edition_id is required when anchor_type is 'variant'"
            )
        return self


class OwnedItemPayload(_PersonalEntityPayload):
    is_digital: bool | None = None
    condition: str | None = Field(default=None, min_length=1, max_length=120)
    grade: str | None = Field(default=None, min_length=1, max_length=64)
    purchase_date: datetime | None = None
    price_paid_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=16)
    personal_notes: str | None = Field(default=None, max_length=4000)
    quantity: int = Field(default=1, ge=1)
    index_number: int | None = Field(default=None, ge=0)
    cover_price_cents: int | None = Field(default=None, ge=0)
    raw_or_slabbed: str | None = Field(default=None, max_length=64)
    grading_company: str | None = Field(default=None, max_length=120)
    grader_notes: str | None = Field(default=None, max_length=4000)
    signed_by: str | None = Field(default=None, max_length=255)
    key_comic: bool = False
    key_reason: str | None = Field(default=None, max_length=4000)
    rating: int | None = Field(default=None, ge=0, le=10)
    read_status: str | None = Field(default=None, min_length=1, max_length=64)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    tags: str | None = Field(default=None, max_length=1000)
    sold_at: datetime | None = None
    sell_price_cents: int | None = Field(default=None, ge=0)
    sold_to: str | None = Field(default=None, max_length=255)
    location_id: str | None = Field(default=None, min_length=1, max_length=120)
    purchase_store: str | None = Field(default=None, max_length=255)
    box_set_id: str | None = Field(default=None, min_length=1, max_length=120)
    box_set_name: str | None = Field(default=None, max_length=255)
    collection_status: str | None = Field(default=None, max_length=64)
    last_bag_board_date: datetime | None = None
    market_value_cents: int | None = Field(default=None, ge=0)

    @field_validator("purchase_date", "started_at", "finished_at", "sold_at", "last_bag_board_date")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None

    @field_validator("finished_at")
    @classmethod
    def validate_finished_at(cls, value: datetime | None, info) -> datetime | None:
        started_at = info.data.get("started_at")
        if value and started_at and value < started_at:
            raise ValueError("finished_at must not be earlier than started_at")
        return value


class WishlistItemPayload(_PersonalEntityPayload):
    target_price_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=16)
    notes: str | None = Field(default=None, max_length=4000)
    created_at: datetime | None = None

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class WatchSessionPayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=120)
    tracking_entry_id: str | None = Field(default=None, min_length=1, max_length=120)
    season_number: int | None = Field(default=None, ge=0)
    episode_number: int | None = Field(default=None, ge=0)
    source_type: TrackingSourceType | None = None
    watched_at: datetime
    seen_where: str | None = Field(default=None, max_length=255)
    rating: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("watched_at")
    @classmethod
    def normalize_watched_at(cls, value: datetime) -> datetime:
        return as_utc(value)


class MetadataOverridePayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=120)
    edition_id: str | None = Field(default=None, min_length=1, max_length=120)
    variant_id: str | None = Field(default=None, min_length=1, max_length=120)
    field_path: str = Field(min_length=1, max_length=255)
    original_value: str | None = Field(default=None, max_length=8000)
    override_value: str = Field(min_length=0, max_length=8000)


class CustomEpisodePayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=120)
    season_number: int = Field(ge=0, le=9999)
    episode_number: int = Field(ge=0, le=99999)
    title: str = Field(min_length=1, max_length=500)
    overview: str | None = Field(default=None, max_length=8000)
    air_date: str | None = Field(default=None, max_length=30)
    runtime_minutes: int | None = Field(default=None, ge=0, le=99999)


class PickListValuePayload(BaseModel):
    list_name: str = Field(min_length=1, max_length=120)
    media_kind: str | None = Field(default=None, max_length=64)
    value: str = Field(min_length=1, max_length=500)
    sort_order: int = Field(default=0, ge=0)


class SyncChangeIn(BaseModel):
    entity_type: str = Field(min_length=1, max_length=80)
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
    def validate_payload_for_entity_type(cls, value: dict[str, Any], info) -> dict[str, Any]:
        entity_type = info.data.get("entity_type")
        action = info.data.get("action")
        if action == "delete":
            return value
        if entity_type == "tracking_entry":
            return TrackingEntryPayload.model_validate(value).model_dump(exclude_none=True)
        if entity_type == "owned_item":
            return OwnedItemPayload.model_validate(value).model_dump(exclude_none=True)
        if entity_type == "wishlist_item":
            return WishlistItemPayload.model_validate(value).model_dump(exclude_none=True)
        if entity_type == "watch_session":
            return WatchSessionPayload.model_validate(value).model_dump(exclude_none=True)
        if entity_type == "metadata_override":
            return MetadataOverridePayload.model_validate(value).model_dump(exclude_none=True)
        if entity_type == "custom_episode":
            return CustomEpisodePayload.model_validate(value).model_dump(exclude_none=True)
        if entity_type == "pick_list_value":
            return PickListValuePayload.model_validate(value).model_dump(exclude_none=True)
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
