import uuid
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, Date, Time, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import RoomType, ScheduleEntryType

class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    building: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType), default=RoomType.CLASSROOM, nullable=False)
    equipment: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False) # e.g. ["PROJECTOR", "AC", "MIC"]
    opening_hours: Mapped[str] = mapped_column(String(100), default="07:00 - 21:00", nullable=False)

    schedule_entries = relationship("ScheduleEntry", back_populates="room")


class ClassSection(Base):
    __tablename__ = "class_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    semester: Mapped[str] = mapped_column(String(20), nullable=False) # e.g. 20251
    lecturer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    lecturer = relationship("User", foreign_keys=[lecturer_id])
    schedule_entries = relationship("ScheduleEntry", back_populates="section")


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("class_sections.id"), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"), index=True, nullable=False)
    entry_type: Mapped[ScheduleEntryType] = mapped_column(Enum(ScheduleEntryType), default=ScheduleEntryType.CLASS, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    section = relationship("ClassSection", back_populates="schedule_entries")
    user = relationship("User", back_populates="schedule_entries")
    room = relationship("Room", back_populates="schedule_entries")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    procedure: Mapped[str] = mapped_column(Text, nullable=False)
    form_urls: Mapped[List[Dict[str, str]]] = mapped_column(JSONB, default=list, nullable=False)
    opening_hours: Mapped[str] = mapped_column(String(100), nullable=False)
    contact: Mapped[str] = mapped_column(String(255), nullable=False)

    unit = relationship("Unit", back_populates="services")

