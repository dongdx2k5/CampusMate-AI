import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    cohort: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Khóa học, ví dụ K65
    major: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Ngành học, ví dụ CNTT
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    unit = relationship("Unit", back_populates="users")
    chat_sessions = relationship("ChatSession", back_populates="user")
    schedule_entries = relationship("ScheduleEntry", back_populates="user")
    feedback_entries = relationship("Feedback", back_populates="user")
    announcement_reads = relationship("AnnouncementRead", back_populates="user")

