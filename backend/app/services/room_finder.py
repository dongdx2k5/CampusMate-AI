from datetime import date, time, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from app.models.schedule import Room, ScheduleEntry

class RoomFinderService:
    """
    Dịch vụ tìm kiếm phòng trống tuân thủ quy tắc nghiệp vụ BR06:
    Một phòng được coi là trống trong khung giờ [date, start_time, end_time]
    khi và chỉ khi KHÔNG tồn tại bất kỳ bản ghi nào trong bảng schedule_entries thỏa mãn:
    entry.date == date AND entry.start_time < end_time AND entry.end_time > start_time.
    """

    @classmethod
    async def find_available_rooms(
        cls,
        db: AsyncSession,
        query_date: date,
        start_t: time,
        end_t: time,
        building: Optional[str] = None,
        min_capacity: Optional[int] = None,
        equipment: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "query_date": query_date,
            "start_t": start_t,
            "end_t": end_t
        }

        extra_filters = []
        if building:
            extra_filters.append("r.building = :building")
            params["building"] = building
        if min_capacity:
            extra_filters.append("r.capacity >= :min_capacity")
            params["min_capacity"] = min_capacity
        if equipment:
            # Kiểm tra equipment JSON array chứa tất cả phần tử yêu cầu
            extra_filters.append("r.equipment @> :equipment::jsonb")
            import json
            params["equipment"] = json.dumps(equipment)

        filter_clause = ("AND " + " AND ".join(extra_filters)) if extra_filters else ""

        # Truy vấn SQL NOT EXISTS kiểm tra giao thoa khung giờ theo chuẩn BR06
        sql = text(f"""
            SELECT r.id, r.code, r.building, r.capacity, r.room_type, r.equipment, r.opening_hours
            FROM rooms r
            WHERE NOT EXISTS (
                SELECT 1
                FROM schedule_entries se
                WHERE se.room_id = r.id
                  AND se.date = :query_date
                  AND se.start_time < :end_t
                  AND se.end_time > :start_t
            )
            {filter_clause}
            ORDER BY r.building, r.code;
        """)

        result = await db.execute(sql, params)
        rows = result.fetchall()

        # Lấy mốc thời gian đồng bộ dữ liệu gần nhất
        sync_stmt = select(func.max(ScheduleEntry.synced_at))
        sync_res = await db.execute(sync_stmt)
        last_synced_at = sync_res.scalar_one_or_none()

        rooms_list = []
        for r in rows:
            rooms_list.append(Room(
                id=r.id,
                code=r.code,
                building=r.building,
                capacity=r.capacity,
                room_type=r.room_type,
                equipment=r.equipment or [],
                opening_hours=r.opening_hours
            ))

        return {
            "lastSyncedAt": last_synced_at or datetime.utcnow(),
            "rooms": rooms_list
        }

