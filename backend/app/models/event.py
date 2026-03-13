from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), default="Podnebni štafetni tek ŠCPET 2024")
    is_active = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Route waypoints stored as JSON [{lat, lng, name, order}]
    route_waypoints = Column(JSON, default=list)

    # Map center
    map_center_lat = Column(Float, default=46.0569)  # Ljubljana
    map_center_lng = Column(Float, default=14.5058)
    map_zoom = Column(Integer, default=13)

    # Photographer alert distance in meters
    photographer_alert_distance = Column(Float, default=300.0)

    # BLE beacon config
    ble_beacons = Column(
        JSON, default=list
    )  # [{uuid, name, lat, lng, checkpoint_name}]

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
