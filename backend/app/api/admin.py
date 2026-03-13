from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.auth import require_admin
from app.models.group import Group
from app.models.event import Event
from app.models.location import LocationUpdate
from app.websocket.manager import manager
import random
import string
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])


def gen_join_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


class GroupCreate(BaseModel):
    name: str
    number: int
    color: str = "#3B82F6"
    member_count: int = 1
    notes: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    member_count: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    route_waypoints: Optional[list] = None
    map_center_lat: Optional[float] = None
    map_center_lng: Optional[float] = None
    map_zoom: Optional[int] = None
    photographer_alert_distance: Optional[float] = None
    ble_beacons: Optional[list] = None
    notes: Optional[str] = None


@router.get("/groups")
async def list_groups(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Group).order_by(Group.number))
    groups = result.scalars().all()
    return [_group_to_dict(g) for g in groups]


@router.post("/groups")
async def create_group(
    data: GroupCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    group = Group(
        name=data.name,
        number=data.number,
        color=data.color,
        member_count=data.member_count,
        notes=data.notes,
        join_code=gen_join_code(),
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    await manager.broadcast_admin_event(
        {"type": "group_created", "group": _group_to_dict(group)}
    )
    return _group_to_dict(group)


@router.patch("/groups/{group_id}")
async def update_group(
    group_id: int,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(404, "Group not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(group, field, val)
    await db.commit()
    await db.refresh(group)
    await manager.broadcast_admin_event(
        {"type": "group_updated", "group": _group_to_dict(group)}
    )
    return _group_to_dict(group)


@router.post("/groups/{group_id}/start")
async def start_group(
    group_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(404, "Group not found")
    group.has_started = True
    group.started_at = datetime.utcnow()
    await db.commit()
    await manager.broadcast_group_status(
        group_id, "started", {"started_at": group.started_at.isoformat()}
    )
    return {"ok": True}


@router.post("/groups/{group_id}/finish")
async def finish_group(
    group_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(404, "Group not found")
    group.has_finished = True
    group.finished_at = datetime.utcnow()
    await db.commit()
    await manager.broadcast_group_status(
        group_id, "finished", {"finished_at": group.finished_at.isoformat()}
    )
    return {"ok": True}


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(404, "Group not found")
    await db.delete(group)
    await db.commit()
    await manager.broadcast_admin_event({"type": "group_deleted", "group_id": group_id})
    return {"ok": True}


@router.get("/event")
async def get_event(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Event).order_by(Event.id.desc()).limit(1))
    event = result.scalar_one_or_none()
    if not event:
        # Auto-create default
        event = Event()
        db.add(event)
        await db.commit()
        await db.refresh(event)
    return _event_to_dict(event)


@router.patch("/event/{event_id}")
async def update_event(
    event_id: int,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Event not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(event, field, val)
    await db.commit()
    await db.refresh(event)
    if data.route_waypoints is not None:
        await manager.broadcast_to_all(
            {
                "type": "route_updated",
                "waypoints": event.route_waypoints or [],
            }
        )
    return _event_to_dict(event)


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from sqlalchemy import func

    groups_total = (await db.execute(select(func.count()).select_from(Group))).scalar()
    groups_active = (
        await db.execute(select(func.count()).select_from(Group).where(Group.is_active))
    ).scalar()
    groups_started = (
        await db.execute(
            select(func.count()).select_from(Group).where(Group.has_started)
        )
    ).scalar()
    groups_finished = (
        await db.execute(
            select(func.count()).select_from(Group).where(Group.has_finished)
        )
    ).scalar()
    loc_count = (
        await db.execute(select(func.count()).select_from(LocationUpdate))
    ).scalar()
    ws_stats = manager.get_stats()
    return {
        "groups": {
            "total": groups_total,
            "active": groups_active,
            "started": groups_started,
            "finished": groups_finished,
        },
        "location_updates": loc_count,
        "websocket": ws_stats,
    }


def _group_to_dict(g: Group) -> dict:
    return {
        "id": g.id,
        "number": g.number,
        "name": g.name,
        "color": g.color,
        "member_count": g.member_count,
        "is_active": g.is_active,
        "has_started": g.has_started,
        "has_finished": g.has_finished,
        "started_at": g.started_at.isoformat() if g.started_at else None,
        "finished_at": g.finished_at.isoformat() if g.finished_at else None,
        "join_code": g.join_code,
        "notes": g.notes,
    }


def _event_to_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "is_active": e.is_active,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "route_waypoints": e.route_waypoints or [],
        "map_center_lat": e.map_center_lat,
        "map_center_lng": e.map_center_lng,
        "map_zoom": e.map_zoom,
        "photographer_alert_distance": e.photographer_alert_distance,
        "ble_beacons": e.ble_beacons or [],
        "notes": e.notes,
    }


@router.get("/photographers")
async def get_photographers(redis=Depends(get_redis), _=Depends(require_admin)):
    connected = [{"id": pid, "online": True} for pid in manager.photographers.keys()]
    connected_ids = set(manager.photographers.keys())
    keys = await redis.keys("photographer_location:*")
    for key in keys:
        pid = key.split(":")[-1]
        if pid not in connected_ids:
            data = await redis.get(key)
            if data:
                import json as _json

                loc = _json.loads(data)
                connected.append(
                    {"id": pid, "online": False, "last_seen": loc.get("ts")}
                )
    pw = await redis.get("photographer_password") or "foto2024"
    return {
        "photographers": connected,
        "password": pw,
        "connected_count": len(manager.photographers),
    }


@router.patch("/photographers/password")
async def set_photographer_password(
    data: dict, redis=Depends(get_redis), _=Depends(require_admin)
):
    new_pw = data.get("password", "").strip()
    if len(new_pw) < 4:
        raise HTTPException(400, "Geslo mora imeti vsaj 4 znake")
    await redis.set("photographer_password", new_pw)
    from app.core.auth import ROLES

    ROLES["photographer"] = new_pw
    return {"ok": True}


class PhotographerAccountCreate(BaseModel):
    name: str
    password: str


@router.get("/photographers/accounts")
async def list_photographer_accounts(
    redis=Depends(get_redis), _=Depends(require_admin)
):
    """List all individual photographer accounts."""
    raw = await redis.hgetall("photographer_accounts")
    names = list(raw.keys()) if raw else []
    # Decode bytes if needed
    names = [k.decode() if isinstance(k, bytes) else k for k in names]
    # Also get online status from manager
    online_set = set(manager.photographers.keys())
    return {"accounts": [{"name": n, "online": n in online_set} for n in names]}


@router.post("/photographers/accounts")
async def create_photographer_account(
    data: PhotographerAccountCreate, redis=Depends(get_redis), _=Depends(require_admin)
):
    """Create a new individual photographer account."""
    name = data.name.strip()
    password = data.password.strip()
    if not name or len(password) < 4:
        raise HTTPException(400, "Ime je obvezno in geslo mora imeti vsaj 4 znake")
    from app.core.auth import pwd_context as _ctx

    hashed = _ctx.hash(password)
    await redis.hset("photographer_accounts", name, hashed)
    return {"ok": True, "name": name}


@router.delete("/photographers/accounts/{name}")
async def delete_photographer_account(
    name: str, redis=Depends(get_redis), _=Depends(require_admin)
):
    """Delete an individual photographer account."""
    deleted = await redis.hdel("photographer_accounts", name)
    if not deleted:
        raise HTTPException(404, "Account not found")
    return {"ok": True}


@router.patch("/photographers/accounts/{name}/password")
async def change_photographer_account_password(
    name: str, data: dict, redis=Depends(get_redis), _=Depends(require_admin)
):
    """Change password for a specific photographer account."""
    new_pw = data.get("password", "").strip()
    if len(new_pw) < 4:
        raise HTTPException(400, "Geslo mora imeti vsaj 4 znake")
    exists = await redis.hexists("photographer_accounts", name)
    if not exists:
        raise HTTPException(404, "Account not found")
    from app.core.auth import pwd_context as _ctx

    hashed = _ctx.hash(new_pw)
    await redis.hset("photographer_accounts", name, hashed)
    return {"ok": True}
