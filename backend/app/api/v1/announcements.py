import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.core.database import get_db
from app.core.security import require_roles
from app.models.user import User
from app.models.announcement import Announcement, AnnouncementRead
from app.models.enums import AnnouncementStatus
from app.schemas.announcement import (
    AnnouncementResponse,
    AnnouncementListResponse,
    AnnouncementReadResponse,
)

router = APIRouter(prefix="/announcements", tags=["Announcements"])

@router.get("", response_model=AnnouncementListResponse)
async def get_student_announcements(
    unread: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(["STUDENT", "LECTURER", "STAFF", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách thông báo dành cho sinh viên.
    Tuân thủ BR04: Chỉ nhìn thấy thông báo cấp toàn trường (SCHOOL) hoặc khớp với unit_id, cohort, major của mình.
    """
    # Lọc thông báo đã PUBLISHED
    base_conditions = [Announcement.status == AnnouncementStatus.PUBLISHED]

    # Điều kiện lọc đối tượng theo BR04
    # Scope == SCHOOL hoặc audience JSON chứa unit_id / cohort / major của user
    scope_cond = Announcement.audience["scope"].astext == "SCHOOL"
    unit_cond = Announcement.audience["scope"].astext == "UNIT"
    
    if current_user.unit_id:
        unit_match = Announcement.unit_id == current_user.unit_id
    else:
        unit_match = False

    audience_filter = or_(scope_cond, and_(unit_cond, unit_match))

    stmt = (
        select(
            Announcement,
            AnnouncementRead.read_at
        )
        .outerjoin(
            AnnouncementRead,
            and_(
                AnnouncementRead.announcement_id == Announcement.id,
                AnnouncementRead.user_id == current_user.id
            )
        )
        .where(and_(*base_conditions, audience_filter))
    )

    if unread:
        stmt = stmt.where(AnnouncementRead.read_at.is_(None))

    stmt = stmt.order_by(Announcement.publish_at.desc(), Announcement.created_at.desc())

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Pagination
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for ann, read_at in rows:
        items.append(AnnouncementResponse(
            id=str(ann.id),
            unitId=str(ann.unit_id),
            title=ann.title,
            body=ann.body,
            audience=ann.audience,
            status=ann.status,
            publishAt=ann.publish_at,
            createdAt=ann.created_at,
            isRead=read_at is not None
        ))

    return AnnouncementListResponse(
        total=total,
        page=page,
        size=size,
        items=items
    )

@router.post("/{id}/read", response_model=AnnouncementReadResponse)
async def mark_announcement_as_read(
    id: str,
    current_user: User = Depends(require_roles(["STUDENT", "LECTURER", "STAFF", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Đánh dấu thông báo đã đọc.
    """
    stmt = select(AnnouncementRead).where(
        AnnouncementRead.announcement_id == id,
        AnnouncementRead.user_id == current_user.id
    )
    res = await db.execute(stmt)
    read_record = res.scalar_one_or_none()

    now = datetime.utcnow()
    if not read_record:
        read_record = AnnouncementRead(
            announcement_id=id,
            user_id=current_user.id,
            read_at=now,
            channel="WEB"
        )
        db.add(read_record)
        await db.commit()
    else:
        now = read_record.read_at

    return AnnouncementReadResponse(readAt=now)

