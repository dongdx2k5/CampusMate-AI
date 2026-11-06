import uuid
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import DocumentStatus, VersionStatus

class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    issuerUnitId: str

class DocumentVersionResponse(BaseModel):
    id: str
    documentId: str
    versionNo: str
    effectiveFrom: date
    effectiveTo: Optional[date] = None
    status: VersionStatus
    fileUrl: str
    indexedAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentResponse(BaseModel):
    id: str
    title: str
    issuerUnitId: str
    issuerUnitName: Optional[str] = None
    status: DocumentStatus
    createdAt: datetime
    activeVersion: Optional[DocumentVersionResponse] = None
    versions: List[DocumentVersionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ReindexRequest(BaseModel):
    versionId: str

