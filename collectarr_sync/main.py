from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from collectarr_sync.config import get_settings
from collectarr_sync.db import CURRENT_SCHEMA_VERSION, initialize_database
from collectarr_sync.schemas import (
    SyncChangesResponse,
    SyncDeviceResponse,
    SyncPullRequest,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncStatusResponse,
    SYNC_PROTOCOL_VERSION,
    as_utc,
)
from collectarr_sync.service import SyncService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_database()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def require_sync_key(
    x_collectarr_sync_key: Annotated[str | None, Header()] = None,
) -> None:
    if x_collectarr_sync_key != get_settings().sync_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sync key",
        )


SyncAuth = Annotated[None, Depends(require_sync_key)]

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class SyncUser:
    """Authenticated sync user. user_id is empty for legacy API-key auth."""

    user_id: str = ""


async def resolve_sync_user(
    x_collectarr_sync_key: Annotated[str | None, Header()] = None,
    bearer: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
) -> SyncUser:
    """Authenticate via API key header *or* JWT Bearer token.

    - API key: legacy mode, returns ``SyncUser(user_id="")``.
    - JWT: decodes token, extracts ``sub`` claim as user_id.
    """
    settings = get_settings()

    # Try API key first (backwards-compatible)
    if x_collectarr_sync_key and x_collectarr_sync_key == settings.sync_api_key:
        return SyncUser()

    # Try JWT Bearer
    if bearer and settings.sync_jwt_secret:
        import jwt as pyjwt

        try:
            payload = pyjwt.decode(
                bearer.credentials,
                settings.sync_jwt_secret,
                algorithms=["HS256"],
            )
        except pyjwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid JWT: {exc}",
            ) from exc
        user_id = payload.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT missing 'sub' claim",
            )
        return SyncUser(user_id=str(user_id))

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication (API key or Bearer token)",
    )


AuthenticatedUser = Annotated[SyncUser, Depends(resolve_sync_user)]


@app.get("/health", tags=["system"])
async def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "protocol_version": SYNC_PROTOCOL_VERSION,
        "schema_version": CURRENT_SCHEMA_VERSION,
    }


@app.get("/sync/status", response_model=SyncStatusResponse, tags=["sync"])
async def sync_status(_: AuthenticatedUser) -> SyncStatusResponse:
    return await SyncService().status(CURRENT_SCHEMA_VERSION)


@app.get("/sync/devices", response_model=list[SyncDeviceResponse], tags=["sync"])
async def sync_devices(_: AuthenticatedUser) -> list[SyncDeviceResponse]:
    return await SyncService().devices()


@app.delete("/sync/devices/{device_id}", tags=["sync"])
async def remove_device(device_id: str, _: AuthenticatedUser) -> dict[str, str | int]:
    removed = await SyncService().remove_device(device_id)
    if removed == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return {"status": "ok", "changes_removed": removed}


@app.get("/sync/pairing-code", tags=["sync"])
async def pairing_code(_: AuthenticatedUser) -> dict[str, str | int]:
    import json as _json

    settings = get_settings()
    code = _json.dumps(
        {
            "protocol_version": SYNC_PROTOCOL_VERSION,
            "sync_base_url": "http://localhost:8020",
            "sync_key": settings.sync_api_key,
        },
        separators=(",", ":"),
    )
    return {"pairing_code": code, "protocol_version": SYNC_PROTOCOL_VERSION}


@app.post("/sync/push", response_model=SyncPushResponse, tags=["sync"])
async def push(payload: SyncPushRequest, user: AuthenticatedUser) -> SyncPushResponse:
    return await SyncService().push(payload, user_id=user.user_id)


@app.post("/sync/pull", response_model=SyncPullResponse, tags=["sync"])
async def pull(payload: SyncPullRequest, user: AuthenticatedUser) -> SyncPullResponse:
    return await SyncService().pull(payload.since, user_id=user.user_id)


@app.get("/sync/changes", response_model=SyncChangesResponse, tags=["sync"])
async def changes(
    since: datetime | None = None, user: AuthenticatedUser = None
) -> SyncChangesResponse:
    normalized_since = as_utc(since) if since else None
    return await SyncService().changes(normalized_since, user_id=user.user_id)
