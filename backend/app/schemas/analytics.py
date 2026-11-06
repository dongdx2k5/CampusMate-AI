import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class QueryClusterResponse(BaseModel):
    id: str
    periodStart: date
    periodEnd: date
    label: str
    size: int
    sampleQuestions: List[str] = []
    isFailedCluster: bool

    model_config = ConfigDict(from_attributes=True)

class AnalyticsSummaryResponse(BaseModel):
    topClusters: List[QueryClusterResponse] = []
    failedClusters: List[QueryClusterResponse] = []
    satisfactionRate: float = 0.0
    totalQuestions: int = 0
    reportedWrongCount: int = 0

class AuditLogResponse(BaseModel):
    id: str
    actorId: Optional[str] = None
    actorName: Optional[str] = None
    action: str
    targetType: str
    targetId: str
    metadata: Optional[Dict[str, Any]] = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditLogListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[AuditLogResponse]

