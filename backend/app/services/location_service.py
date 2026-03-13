import json
import math
from typing import Optional, List
from datetime import datetime
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.location import LocationUpdate, LocationSource
from app.models.group import Group
from app.models.event import Event
from app.websocket.manager import manager
import logging

logger = logging.getLogger(__name__)

LOCATION_CACHE_PREFIX = "group_location:"
LOCATION_HISTORY_PREFIX = "group_history:"
HISTORY_MAX_POINTS = 100  # Keep last N points in Redis for trail


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class LocationService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    async def process_location_update(
        self,
        group_id: int,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None,
        altitude: Optional[float] = None,
        source: LocationSource = LocationSource.gps,
        device_id: Optional[str] = None,
        submitted_by: str = "participant",
        photographer_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> dict:
        """Process incoming location update, persist, cache, and broadcast."""

        # 1. Persist to DB
        loc = LocationUpdate(
            group_id=group_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            altitude=altitude,
            source=source,
            device_id=device_id,
            submitted_by=submitted_by,
            photographer_id=photographer_id,
            timestamp=timestamp or datetime.utcnow(),
        )
        self.db.add(loc)
        await self.db.commit()
        await self.db.refresh(loc)

        # 2. Update Redis cache (latest position)
        location_data = {
            "lat": latitude,
            "lng": longitude,
            "accuracy": accuracy,
            "altitude": altitude,
            "source": source.value,
            "timestamp": loc.timestamp.isoformat(),
            "submitted_by": submitted_by,
        }
        await self.redis.setex(
            f"{LOCATION_CACHE_PREFIX}{group_id}",
            3600,  # 1h expiry
            json.dumps(location_data),
        )

        # 3. Append to trail history
        await self.redis.lpush(
            f"{HISTORY_PREFIX}{group_id}",
            json.dumps({"lat": latitude, "lng": longitude, "ts": loc.timestamp.isoformat()}),
        )
        await self.redis.ltrim(f"{HISTORY_PREFIX}{group_id}", 0, HISTORY_MAX_POINTS - 1)
        await self.redis.expire(f"{HISTORY_PREFIX}{group_id}", 3600 * 8)

        # 4. Broadcast via WebSocket
        await manager.broadcast_location_update(group_id, location_data)

        # 5. Check photographer proximity alerts
        await self._check_photographer_alerts(group_id, latitude, longitude)

        return location_data

    async def process_offline_batch(self, group_id: int, updates: list, device_id: str) -> int:
        """Process a batch of offline location updates in chronological order."""
        updates_sorted = sorted(updates, key=lambda x: x.get("timestamp", ""))
        count = 0
        for update in updates_sorted:
            try:
                ts = datetime.fromisoformat(update["timestamp"]) if "timestamp" in update else None
                await self.process_location_update(
                    group_id=group_id,
                    latitude=update["lat"],
                    longitude=update["lng"],
                    accuracy=update.get("accuracy"),
                    altitude=update.get("altitude"),
                    source=LocationSource(update.get("source", "gps")),
                    device_id=device_id,
                    submitted_by="participant",
                    timestamp=ts,
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to process offline update: {e}")
        return count

    async def get_all_latest_locations(self) -> dict:
        """Get latest location for all active groups from Redis."""
        result = {}
        keys = await self.redis.keys(f"{LOCATION_CACHE_PREFIX}*")
        for key in keys:
            group_id = int(key.split(":")[-1])
            data = await self.redis.get(key)
            if data:
                result[group_id] = json.loads(data)
        return result

    async def get_group_trail(self, group_id: int) -> List[dict]:
        """Get recent trail points for a group."""
        points = await self.redis.lrange(f"{HISTORY_PREFIX}{group_id}", 0, HISTORY_MAX_POINTS - 1)
        return [json.loads(p) for p in points]

    async def get_full_state(self) -> dict:
        """Snapshot of all groups with latest positions for new WS connections."""
        result = await self.db.execute(select(Group).where(Group.is_active))
        groups = result.scalars().all()

        locations = await self.get_all_latest_locations()

        groups_data = []
        for g in groups:
            trail = await self.get_group_trail(g.id)
            groups_data.append({
                "id": g.id,
                "number": g.number,
                "name": g.name,
                "color": g.color,
                "member_count": g.member_count,
                "has_started": g.has_started,
                "has_finished": g.has_finished,
                "started_at": g.started_at.isoformat() if g.started_at else None,
                "location": locations.get(g.id),
                "trail": trail,
            })

        return {"groups": groups_data}

    async def _check_photographer_alerts(self, group_id: int, lat: float, lng: float):
        """Check if any photographer is within alert distance of the group."""
        # Get alert distance from event config
        event_result = await self.db.execute(select(Event).where(Event.is_active))
        event = event_result.scalar_one_or_none()
        if not event:
            return

        alert_distance = event.photographer_alert_distance or 300.0

        # Get group info
        group_result = await self.db.execute(select(Group).where(Group.id == group_id))
        group = group_result.scalar_one_or_none()
        if not group:
            return

        # Check each photographer's cached location
        photo_keys = await self.redis.keys("photographer_location:*")
        for key in photo_keys:
            photographer_id = key.split(":")[-1]
            data = await self.redis.get(key)
            if not data:
                continue
            photo_loc = json.loads(data)
            dist = haversine_distance(lat, lng, photo_loc["lat"], photo_loc["lng"])
            if dist <= alert_distance:
                await manager.alert_photographer(
                    photographer_id=photographer_id,
                    group_id=group_id,
                    distance=dist,
                    group_name=f"Skupina {group.number} – {group.name}",
                )

    async def update_photographer_location(self, photographer_id: str, lat: float, lng: float):
        """Cache photographer's current position."""
        await self.redis.setex(
            f"photographer_location:{photographer_id}",
            300,  # 5 min expiry
            json.dumps({"lat": lat, "lng": lng, "ts": datetime.utcnow().isoformat()}),
        )


HISTORY_PREFIX = "group_history:"
