from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.schedule import Service
from app.models.unit import Unit
from app.schemas.service import ServiceListResponse, ServiceItemResponse

router = APIRouter(prefix="/services", tags=["Services & Procedures"])

@router.get("", response_model=ServiceListResponse)
async def get_services(
    q: Optional[str] = Query(None, description="Từ khóa tra cứu thủ tục"),
    unit_id: Optional[str] = Query(None, alias="unitId"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Tra cứu danh bạ dịch vụ & thủ tục hành chính sinh viên.
    """
    stmt = select(Service, Unit.name.label("unit_name")).join(Unit, Service.unit_id == Unit.id)

    if q:
        stmt = stmt.where(
            or_(
                Service.name.ilike(f"%{q}%"),
                Service.procedure.ilike(f"%{q}%")
            )
        )
    if unit_id:
        stmt = stmt.where(Service.unit_id == unit_id)

    stmt = stmt.order_by(Service.name)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for s, u_name in rows:
        items.append(ServiceItemResponse(
            id=str(s.id),
            unitId=str(s.unit_id),
            unitName=u_name,
            name=s.name,
            procedure=s.procedure,
            formUrls=s.form_urls or [],
            openingHours=s.opening_hours,
            contact=s.contact
        ))

    return ServiceListResponse(services=items)

