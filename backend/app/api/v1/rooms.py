from datetime import date, time
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_roles
from app.models.user import User
from app.schemas.schedule import AvailableRoomsResponse
from app.services.room_finder import RoomFinderService

router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.get("/available", response_model=AvailableRoomsResponse)
async def get_available_rooms(
    query_date: date = Query(..., alias="date", description="Ngày cần tra cứu (YYYY-MM-DD)"),
    start: str = Query(..., description="Giờ bắt đầu (HH:MM), ví dụ 08:00"),
    end: str = Query(..., description="Giờ kết thúc (HH:MM), ví dụ 10:00"),
    building: Optional[str] = Query(None, description="Tòa nhà (ví dụ: A1, B1, D3)"),
    capacity: Optional[int] = Query(None, description="Sức chứa tối thiểu"),
    equipment: Optional[List[str]] = Query(None, description="Danh sách thiết bị yêu cầu"),
    current_user: User = Depends(require_roles(["STUDENT", "LECTURER", "STAFF", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Truy vấn tìm phòng trống tuân thủ quy tắc nghiệp vụ BR06.
    Kiểm tra giao thoa khung giờ với schedule_entries (lịch học, lịch thi, lịch đặt phòng).
    """
    # Parse time
    s_hour, s_min = map(int, start.split(":"))
    e_hour, e_min = map(int, end.split(":"))
    start_t = time(s_hour, s_min)
    end_t = time(e_hour, e_min)

    result = await RoomFinderService.find_available_rooms(
        db=db,
        query_date=query_date,
        start_t=start_t,
        end_t=end_t,
        building=building,
        min_capacity=capacity,
        equipment=equipment
    )

    return result

