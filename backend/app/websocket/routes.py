from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websocket.manager import manager
from app.core.auth import verify_token
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.services.location_service import LocationService
import json
import logging

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    """Public live map viewer WebSocket."""
    await manager.connect_viewer(websocket)
    try:
        # Send full state snapshot on connect
        async with AsyncSessionLocal() as db:
            service = LocationService(db, await get_redis())
            state = await service.get_full_state()
        await manager.broadcast_full_state(websocket, state)
        # Broadcast updated viewer count to all viewers
        await manager.broadcast_to_all({"type": "viewer_count", "count": len(manager.viewers)})

        while True:
            # Viewers just receive, we keep connection alive via ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_viewer(websocket)
        # Broadcast updated viewer count after disconnect
        await manager.broadcast_to_all({"type": "viewer_count", "count": len(manager.viewers)})


@router.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket, token: str = Query(default=None)):
    """Admin panel WebSocket."""
    if not token:
        token = websocket.cookies.get("st_token")
    try:
        payload = verify_token(token) if token else None
        if not payload or payload.get("role") != "admin":
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect_admin(websocket)
    try:
        async with AsyncSessionLocal() as db:
            service = LocationService(db, await get_redis())
            state = await service.get_full_state()
        await manager.broadcast_full_state(websocket, state)

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)


@router.websocket("/ws/photographer/{photographer_id}")
async def ws_photographer(websocket: WebSocket, photographer_id: str, token: str = Query(default=None)):
    """Photographer WebSocket — receives group proximity alerts."""
    if not token:
        token = websocket.cookies.get("st_token")
    try:
        payload = verify_token(token) if token else None
        if not payload or payload.get("role") not in ("photographer", "admin"):
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect_photographer(websocket, photographer_id)
    try:
        async with AsyncSessionLocal() as db:
            service = LocationService(db, await get_redis())
            state = await service.get_full_state()
        await manager.broadcast_full_state(websocket, state)

        while True:
            raw = await websocket.receive_text()
            if raw == "ping":
                await websocket.send_text("pong")
                continue
            try:
                msg = json.loads(raw)
                # Photographer can send their own location via WS too
                if msg.get("type") == "location":
                    async with AsyncSessionLocal() as db:
                        service = LocationService(db, await get_redis())
                        await service.update_photographer_location(
                            photographer_id, msg["lat"], msg["lng"]
                        )
                        # If they're pinning a group location
                        if "group_id" in msg:
                            from app.models.location import LocationSource
                            await service.process_location_update(
                                group_id=msg["group_id"],
                                latitude=msg["lat"],
                                longitude=msg["lng"],
                                source=LocationSource.photographer,
                                submitted_by="photographer",
                                photographer_id=photographer_id,
                            )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_photographer(photographer_id)


@router.websocket("/ws/group/{group_id}")
async def ws_group(websocket: WebSocket, group_id: int, token: str = Query(default=None)):
    """Participant group WebSocket — receives group status updates."""
    if not token:
        token = websocket.cookies.get("st_token")
    try:
        payload = verify_token(token) if token else None
        if not payload or payload.get("role") != "participant" or payload.get("group_id") != group_id:
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect_participant(websocket, group_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_participant(websocket, group_id)
