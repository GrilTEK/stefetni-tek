from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class LocationSource(str, enum.Enum):
    gps = "gps"
    bluetooth = "bluetooth"
    manual = "manual"
    photographer = "photographer"


class LocationUpdate(Base):
    __tablename__ = "location_updates"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    altitude = Column(Float, nullable=True)
    source = Column(Enum(LocationSource), default=LocationSource.gps)
    device_id = Column(String(100), nullable=True)  # Which phone submitted
    submitted_by = Column(String(50), nullable=True)  # "participant" | "photographer"
    photographer_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="locations")
