import uuid
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from icalendar import Calendar, Event

from app.models.schedule import ScheduleEntry, ClassSection, Room
from app.models.enums import ScheduleEntryType

class SISSyncService:
    """
    Dịch vụ đồng bộ và truy vấn lịch học/lịch thi cá nhân tuân thủ quy tắc nghiệp vụ BR04
    (Cô lập dữ liệu cá nhân: người dùng chỉ được xem lịch của chính mình).
    """

    @classmethod
    async def get_user_schedule(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        stmt = (
            select(
                ScheduleEntry,
                ClassSection.course_code,
                ClassSection.course_name,
                Room.code.label("room_code"),
                Room.building
            )
            .outerjoin(ClassSection, ScheduleEntry.section_id == ClassSection.id)
            .join(Room, ScheduleEntry.room_id == Room.id)
            .where(ScheduleEntry.user_id == user_id)
        )

        if from_date:
            stmt = stmt.where(ScheduleEntry.date >= from_date)
        if to_date:
            stmt = stmt.where(ScheduleEntry.date <= to_date)

        stmt = stmt.order_by(ScheduleEntry.date, ScheduleEntry.start_time)
        result = await db.execute(stmt)
        rows = result.all()

        sync_stmt = (
            select(func.max(ScheduleEntry.synced_at))
            .where(ScheduleEntry.user_id == user_id)
        )
        sync_res = await db.execute(sync_stmt)
        last_synced_at = sync_res.scalar_one_or_none() or datetime.utcnow()

        entries = []
        for row in rows:
            entry = row.ScheduleEntry
            entries.append({
                "id": str(entry.id),
                "courseCode": row.course_code,
                "courseName": row.course_name or ("Lịch thi" if entry.entry_type == ScheduleEntryType.EXAM else "Sự kiện"),
                "roomCode": row.room_code,
                "building": row.building,
                "entryType": entry.entry_type,
                "date": entry.date,
                "startTime": entry.start_time,
                "endTime": entry.end_time
            })

        return {
            "lastSyncedAt": last_synced_at,
            "entries": entries
        }

    @classmethod
    async def export_icalendar(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        semester: Optional[str] = None
    ) -> bytes:
        """
        Xuất lịch cá nhân chuẩn định dạng text/calendar (.ics) theo RFC 5545
        """
        data = await cls.get_user_schedule(db, user_id)
        entries = data.get("entries", [])

        cal = Calendar()
        cal.add('prodid', '-//CampusMate AI//Lịch Cá Nhân Đại Học//VI')
        cal.add('version', '2.0')

        for e in entries:
            event = Event()
            event.add('summary', f"[{e['entryType']}] {e['courseName']}")
            event.add('location', f"Phòng {e['roomCode']}, Tòa {e['building']}")
            
            # Ghép date và time
            start_dt = datetime.combine(e['date'], e['startTime'])
            end_dt = datetime.combine(e['date'], e['endTime'])
            
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)
            event.add('dtstamp', datetime.utcnow())
            event['uid'] = f"{e['id']}@campusmate.uni.edu.vn"
            event.add('description', f"Mã môn: {e.get('courseCode') or 'N/A'}\nLoại: {e['entryType']}")

            cal.add_component(event)

        return cal.to_ical()

