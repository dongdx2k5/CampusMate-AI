import uuid
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.announcement import Announcement
from app.models.enums import AnnouncementStatus, UserRole
from app.models.user import User
from app.models.analytics import AuditLog

class AnnouncementFSM:
    """
    Máy trạng thái duyệt thông báo tuân thủ quy tắc nghiệp vụ BR05:
    - Vòng đời: DRAFT -> PENDING_APPROVAL -> SCHEDULED -> PUBLISHED -> REVOKED
    - Thông báo cấp đơn vị (scope == 'UNIT'): Cán bộ/Trưởng đơn vị có thể đăng trực tiếp.
    - Thông báo cấp toàn trường (scope == 'SCHOOL'): Bắt buộc chuyển PENDING_APPROVAL
      và phải được UNIT_HEAD hoặc ADMIN phê duyệt trước khi PUBLISHED.
    - Tuyệt đối không xóa cứng (hard-delete); chỉ chuyển sang REVOKED để lưu vết kiểm toán.
    """

    @classmethod
    async def create_announcement(
        cls,
        db: AsyncSession,
        author: User,
        title: str,
        body: str,
        audience: dict,
        publish_at: Optional[datetime] = None
    ) -> Announcement:
        scope = audience.get("scope", "SCHOOL")
        
        # Nếu là thông báo toàn trường mà không phải ADMIN, tạo ở trạng thái PENDING_APPROVAL
        # Nếu là thông báo cấp UNIT, tác giả có thể lưu DRAFT hoặc PENDING_APPROVAL
        initial_status = AnnouncementStatus.DRAFT

        announcement = Announcement(
            unit_id=author.unit_id,
            author_id=author.id,
            title=title,
            body=body,
            audience=audience,
            status=initial_status,
            publish_at=publish_at
        )
        db.add(announcement)
        await db.flush()

        # Ghi nhật ký kiểm toán
        audit = AuditLog(
            actor_id=author.id,
            action="CREATE_ANNOUNCEMENT",
            target_type="ANNOUNCEMENT",
            target_id=str(announcement.id),
            metadata_={"status": initial_status.value, "scope": scope}
        )
        db.add(audit)
        await db.commit()
        await db.refresh(announcement)
        return announcement

    @classmethod
    async def publish_announcement(
        cls,
        db: AsyncSession,
        announcement_id: str,
        current_user: User
    ) -> Announcement:
        res = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
        announcement = res.scalar_one_or_none()
        if not announcement:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")

        if announcement.status == AnnouncementStatus.REVOKED:
            raise HTTPException(status_code=400, detail="Thông báo đã bị thu hồi, không thể đăng lại.")

        scope = announcement.audience.get("scope", "SCHOOL")
        user_role = current_user.role

        # Kiểm tra thẩm quyền phê duyệt theo BR05
        if scope == "SCHOOL":
            if user_role not in [UserRole.ADMIN]:
                # Chuyển trạng thái sang PENDING_APPROVAL nếu chưa phải admin duyệt
                announcement.status = AnnouncementStatus.PENDING_APPROVAL
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Thông báo cấp toàn trường bắt buộc phải do Quản trị viên / Trưởng đơn vị phê duyệt. Đã chuyển sang PENDING_APPROVAL."
                )

        # Chuyển sang PUBLISHED hoặc SCHEDULED nếu có hẹn giờ tương lai
        now = datetime.utcnow()
        if announcement.publish_at and announcement.publish_at > now:
            announcement.status = AnnouncementStatus.SCHEDULED
        else:
            announcement.status = AnnouncementStatus.PUBLISHED
            announcement.publish_at = now

        announcement.approved_by = current_user.id

        audit = AuditLog(
            actor_id=current_user.id,
            action="PUBLISH_ANNOUNCEMENT",
            target_type="ANNOUNCEMENT",
            target_id=str(announcement.id),
            metadata_={"status": announcement.status.value, "scope": scope}
        )
        db.add(audit)
        await db.commit()
        await db.refresh(announcement)
        return announcement

    @classmethod
    async def revoke_announcement(
        cls,
        db: AsyncSession,
        announcement_id: str,
        current_user: User,
        reason: str
    ) -> Announcement:
        res = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
        announcement = res.scalar_one_or_none()
        if not announcement:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")

        # BR05: Không hard delete, chỉ đổi status thành REVOKED
        announcement.status = AnnouncementStatus.REVOKED

        audit = AuditLog(
            actor_id=current_user.id,
            action="REVOKE_ANNOUNCEMENT",
            target_type="ANNOUNCEMENT",
            target_id=str(announcement.id),
            metadata_={"reason": reason}
        )
        db.add(audit)
        await db.commit()
        await db.refresh(announcement)
        return announcement

