from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    number = Column(Integer, unique=True, nullable=False)  # Group number e.g. 1-20
    color = Column(String(7), default="#3B82F6")  # Hex color for map marker
    member_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    has_started = Column(Boolean, default=False)
    has_finished = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    join_code = Column(String(8), unique=True, nullable=False)  # e.g. "GRP001"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    locations = relationship("LocationUpdate", back_populates="group", cascade="all, delete-orphan")
