import uuid
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict

class ServiceItemResponse(BaseModel):
    id: str
    unitId: str
    unitName: Optional[str] = None
    name: str
    procedure: str
    formUrls: List[Dict[str, str]] = []
    openingHours: str
    contact: str

    model_config = ConfigDict(from_attributes=True)

class ServiceListResponse(BaseModel):
    services: List[ServiceItemResponse] = []

