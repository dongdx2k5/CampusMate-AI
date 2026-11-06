from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_roles
from app.models.user import User
from app.schemas.schedule import ScheduleResponse
from app.services.sis_sync import SISSyncService

router = APIRouter(prefix="/schedule", tags=["Schedule"])

@router.get("", response_model=ScheduleResponse)
async def get_schedule(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    current_user: User = Depends(require_roles(["STUDENT", "LECTURER", "STAFF", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Xem lịch học/lịch thi cá nhân.
    Tuân thủ BR04: Người dùng CHỈ được truy vấn lịch của chính mình.
    """
    schedule_data = await SISSyncService.get_user_schedule(
        db=db,
        user_id=current_user.id,
        from_date=from_date,
        to_date=to_date
    )
    return schedule_data

@router.get("/export.ics")
async def export_schedule_ics(
    semester: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["STUDENT", "LECTURER", "STAFF", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Xuất lịch cá nhân chuẩn định dạng text/calendar (.ics) để đồng bộ vào Google Calendar / Apple Calendar.
    """
    ics_bytes = await SISSyncService.export_icalendar(
        db=db,
        user_id=current_user.id,
        semester=semester
    )
    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=schedule_{semester or 'all'}.ics"
        }
    )

