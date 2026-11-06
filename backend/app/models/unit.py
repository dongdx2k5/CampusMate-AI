import uuid
from sqlalchemy import String, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.enums import UnitKind

class Unit(Base):
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[UnitKind] = mapped_column(Enum(UnitKind), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    office_location: Mapped[str] = mapped_column(String(255), nullable=True)

    users = relationship("User", back_populates="unit")
    documents = relationship("Document", back_populates="issuer_unit")
    announcements = relationship("Announcement", back_populates="unit")
    services = relationship("Service", back_populates="unit")

