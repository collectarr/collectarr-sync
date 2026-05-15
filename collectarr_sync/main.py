from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health", tags=["system"])
async def health() -> dict[str, str | int]:
    return {"status": "ok", "schema_version": CURRENT_SCHEMA_VERSION}


@app.get("/sync/status", response_model=SyncStatusResponse, tags=["sync"])
async def sync_status(_: SyncAuth) -> SyncStatusResponse:
    return await SyncService().status(CURRENT_SCHEMA_VERSION)


@app.get("/sync/devices", response_model=list[SyncDeviceResponse], tags=["sync"])
async def sync_devices(_: SyncAuth) -> list[SyncDeviceResponse]:
    return await SyncService().devices()


@app.post("/sync/push", response_model=SyncPushResponse, tags=["sync"])
async def push(payload: SyncPushRequest, _: SyncAuth) -> SyncPushResponse:
    return await SyncService().push(payload)


@app.post("/sync/pull", response_model=SyncPullResponse, tags=["sync"])
async def pull(payload: SyncPullRequest, _: SyncAuth) -> SyncPullResponse:
    return await SyncService().pull(payload.since)


@app.get("/sync/changes", response_model=SyncChangesResponse, tags=["sync"])
async def changes(since: datetime | None = None, _: SyncAuth = None) -> SyncChangesResponse:
    normalized_since = as_utc(since) if since else None
    return await SyncService().changes(normalized_since)
