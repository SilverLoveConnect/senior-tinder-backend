# 신고 모델
import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ReportStatusEnum(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    resolved = "resolved"


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reported_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReportStatusEnum] = mapped_column(
        SAEnum(ReportStatusEnum), default=ReportStatusEnum.pending, nullable=False
    )

    reporter: Mapped["User"] = relationship(
        "User", foreign_keys=[reporter_id], back_populates="reports_sent", lazy="select"
    )
    reported: Mapped["User"] = relationship(
        "User", foreign_keys=[reported_id], back_populates="reports_received", lazy="select"
    )
