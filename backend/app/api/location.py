from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.auth import verify_token
from app.services.location_service import LocationService
from app.models.location import LocationSource
from app.models.group import Group
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

router = APIRouter(prefix="/location", tags=["location"])
security = HTTPBearer()


def get_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    return verify_token(credentials.credentials)


class LocationPayload(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    source: LocationSource = LocationSource.gps
    timestamp: Optional[datetime] = None


class OfflineBatch(BaseModel):
    updates: List[dict]


@router.post("/update")
async def update_location(
    payload: LocationPayload,
    token: dict = Depends(get_token),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    """Single location update from participant or photographer."""
    service = LocationService(db, redis)

    role = token.get("role")
    if role == "participant":
        group_id = token.get("group_id")
        if not group_id:
            raise HTTPException(status_code=400, detail="No group in token")
        # Only accept location updates after admin has started the group
        group_result = await db.execute(select(Group).where(Group.id == group_id))
        group = group_result.scalar_one_or_none()
        if not group or not group.has_started:
            return {"ok": True, "skipped": "not_started"}
        await service.process_location_update(
            group_id=group_id,
            latitude=payload.lat,
            longitude=payload.lng,
            accuracy=payload.accuracy,
            altitude=payload.altitude,
            source=payload.source,
            device_id=token.get("device_id"),
            submitted_by="participant",
            timestamp=payload.timestamp,
        )
        return {"ok": True}

    elif role in ("photographer", "admin"):
        # Photographer updates own location + optionally group location
        photographer_id = token.get("photographer_id", "unknown")
        await service.update_photographer_location(photographer_id, payload.lat, payload.lng)
        return {"ok": True}

    raise HTTPException(status_code=403, detail="Not allowed")


@router.post("/update-group/{group_id}")
async def photographer_update_group(
    group_id: int,
    payload: LocationPayload,
    token: dict = Depends(get_token),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    """Photographer manually pins a group's location."""
    if token.get("role") not in ("photographer", "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")

    service = LocationService(db, redis)
    await service.process_location_update(
        group_id=group_id,
        latitude=payload.lat,
        longitude=payload.lng,
        accuracy=payload.accuracy,
        source=LocationSource.photographer,
        submitted_by="photographer",
        photographer_id=token.get("photographer_id"),
        timestamp=payload.timestamp,
    )
    return {"ok": True}


@router.post("/sync-offline")
async def sync_offline(
    batch: OfflineBatch,
    token: dict = Depends(get_token),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    """Sync offline location batch from participant device."""
    if token.get("role") != "participant":
        raise HTTPException(status_code=403, detail="Only participants can sync offline data")

    group_id = token.get("group_id")
    device_id = token.get("device_id", "unknown")

    # Only sync if group has started
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group or not group.has_started:
        return {"synced": 0, "skipped": "not_started"}

    service = LocationService(db, redis)
    count = await service.process_offline_batch(group_id, batch.updates, device_id)
    return {"synced": count}


@router.get("/trail/{group_id}")
async def get_trail(group_id: int, db=Depends(get_db), redis=Depends(get_redis)):
    """Get recent GPS trail for a group (public)."""
    service = LocationService(db, redis)
    trail = await service.get_group_trail(group_id)
    return {"trail": trail}
