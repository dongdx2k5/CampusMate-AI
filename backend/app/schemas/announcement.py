import uuid
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import AnnouncementStatus

class AnnouncementAudience(BaseModel):
    scope: Literal["SCHOOL", "UNIT"] = "SCHOOL"
    unit_ids: List[str] = []
    cohorts: List[str] = []
    majors: List[str] = []

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    body: str = Field(..., min_length=5)
    audience: AnnouncementAudience
    publishAt: Optional[datetime] = None

class AnnouncementRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=3)

class AnnouncementResponse(BaseModel):
    id: str
    unitId: str
    unitName: Optional[str] = None
    title: str
    body: str
    audience: AnnouncementAudience
    status: AnnouncementStatus
    publishAt: Optional[datetime] = None
    createdAt: datetime
    isRead: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)

class AnnouncementListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[AnnouncementResponse]

class AnnouncementReadResponse(BaseModel):
    readAt: datetime

