import json
import asyncio
from typing import Dict, Set, Any
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # viewers: all public live map viewers
        self.viewers: Set[WebSocket] = set()
        # admins: admin panel connections
        self.admins: Set[WebSocket] = set()
        # photographers: keyed by photographer_id
        self.photographers: Dict[str, WebSocket] = {}
        # participants: keyed by group_id -> set of websockets
        self.participants: Dict[int, Set[WebSocket]] = {}

    # --- Connect / Disconnect ---

    async def connect_viewer(self, ws: WebSocket):
        await ws.accept()
        self.viewers.add(ws)
        logger.info(f"Viewer connected. Total viewers: {len(self.viewers)}")

    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self.admins.add(ws)
        logger.info(f"Admin connected.")

    async def connect_photographer(self, ws: WebSocket, photographer_id: str):
        await ws.accept()
        self.photographers[photographer_id] = ws
        logger.info(f"Photographer {photographer_id} connected.")

    async def connect_participant(self, ws: WebSocket, group_id: int):
        await ws.accept()
        if group_id not in self.participants:
            self.participants[group_id] = set()
        self.participants[group_id].add(ws)
        logger.info(f"Participant connected to group {group_id}. Group size: {len(self.participants[group_id])}")

    def disconnect_viewer(self, ws: WebSocket):
        self.viewers.discard(ws)

    def disconnect_admin(self, ws: WebSocket):
        self.admins.discard(ws)

    def disconnect_photographer(self, photographer_id: str):
        self.photographers.pop(photographer_id, None)

    def disconnect_participant(self, ws: WebSocket, group_id: int):
        if group_id in self.participants:
            self.participants[group_id].discard(ws)
            if not self.participants[group_id]:
                del self.participants[group_id]

    # --- Broadcast methods ---

    async def _send(self, ws: WebSocket, data: dict):
        try:
            await ws.send_json(data)
        except Exception:
            pass  # Connection already closed

    async def broadcast_location_update(self, group_id: int, location_data: dict):
        """Broadcast a group's new location to all viewers, admins, photographers."""
        msg = {"type": "location_update", "group_id": group_id, **location_data}
        await self._broadcast_to_set(self.viewers, msg)
        await self._broadcast_to_set(self.admins, msg)
        await self._broadcast_to_dict(self.photographers, msg)

    async def broadcast_group_status(self, group_id: int, status: str, data: dict = None):
        """Broadcast group started/finished/paused etc."""
        msg = {"type": "group_status", "group_id": group_id, "status": status, **(data or {})}
        await self._broadcast_to_set(self.viewers, msg)
        await self._broadcast_to_set(self.admins, msg)
        await self._broadcast_to_dict(self.photographers, msg)
        if group_id in self.participants:
            await self._broadcast_to_set(self.participants[group_id], msg)

    async def broadcast_admin_event(self, data: dict):
        """Broadcast admin-only events."""
        await self._broadcast_to_set(self.admins, data)

    async def broadcast_to_all(self, data: dict):
        """Broadcast to all connected clients (viewers, admins, photographers)."""
        await self._broadcast_to_set(self.viewers, data)
        await self._broadcast_to_set(self.admins, data)
        await self._broadcast_to_dict(self.photographers, data)

    async def alert_photographer(self, photographer_id: str, group_id: int, distance: float, group_name: str):
        """Send proximity alert to a specific photographer."""
        if photographer_id in self.photographers:
            msg = {
                "type": "proximity_alert",
                "group_id": group_id,
                "group_name": group_name,
                "distance_meters": round(distance),
            }
            await self._send(self.photographers[photographer_id], msg)

    async def send_to_group_participants(self, group_id: int, data: dict):
        """Send message to all devices in a specific group."""
        if group_id in self.participants:
            await self._broadcast_to_set(self.participants[group_id], data)

    async def broadcast_full_state(self, ws: WebSocket, state: dict):
        """Send full state snapshot to a newly connected client."""
        await self._send(ws, {"type": "full_state", **state})

    async def _broadcast_to_set(self, connections: Set[WebSocket], data: dict):
        dead = set()
        tasks = []
        for ws in connections:
            tasks.append(self._send(ws, data))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _broadcast_to_dict(self, connections: Dict[str, WebSocket], data: dict):
        tasks = [self._send(ws, data) for ws in connections.values()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_stats(self) -> dict:
        return {
            "viewers": len(self.viewers),
            "admins": len(self.admins),
            "photographers": len(self.photographers),
            "participant_groups": len(self.participants),
            "total_participant_devices": sum(len(s) for s in self.participants.values()),
        }


manager = ConnectionManager()
