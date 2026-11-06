import uuid
from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.enums import ScheduleEntryType, RoomType

class ScheduleEntryItem(BaseModel):
    id: str
    courseCode: Optional[str] = None
    courseName: Optional[str] = None
    roomCode: str
    building: str
    entryType: ScheduleEntryType
    date: date
    startTime: time
    endTime: time

class ScheduleResponse(BaseModel):
    lastSyncedAt: Optional[datetime] = None
    entries: List[ScheduleEntryItem] = []

class RoomResponse(BaseModel):
    id: str
    code: str
    building: str
    capacity: int
    roomType: RoomType
    equipment: List[str] = []
    openingHours: str

    model_config = ConfigDict(from_attributes=True)

class AvailableRoomsResponse(BaseModel):
    lastSyncedAt: Optional[datetime] = None
    rooms: List[RoomResponse] = []

