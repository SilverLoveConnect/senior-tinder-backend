# 매너 점수 변동 내역 모델
import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class MannerFactorEnum(str, enum.Enum):
    response_rate = "response_rate"
    report = "report"
    profile = "profile"
    verified = "verified"
    activity = "activity"


class MannerHistory(Base, TimestampMixin):
    __tablename__ = "manner_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    factor: Mapped[MannerFactorEnum] = mapped_column(SAEnum(MannerFactorEnum), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="manner_histories", lazy="select")
