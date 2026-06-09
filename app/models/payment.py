# 결제, 구독, 배지, 부스트 모델
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PaymentTypeEnum(str, enum.Enum):
    point = "point"
    subscription = "subscription"
    badge = "badge"
    boost = "boost"


class PaymentStatusEnum(str, enum.Enum):
    paid = "paid"
    failed = "failed"
    cancelled = "cancelled"


class SubscriptionPlanEnum(str, enum.Enum):
    basic = "basic"
    gold = "gold"


class SubscriptionStatusEnum(str, enum.Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    imp_uid: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[PaymentTypeEnum] = mapped_column(
        SAEnum(PaymentTypeEnum), nullable=False
    )
    status: Mapped[PaymentStatusEnum] = mapped_column(
        SAEnum(PaymentStatusEnum), default=PaymentStatusEnum.paid, nullable=False
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="payments", lazy="select"
    )
    badge: Mapped["Badge | None"] = relationship(
        "Badge", back_populates="payment", uselist=False, lazy="select"
    )
    boost: Mapped["Boost | None"] = relationship(
        "Boost", back_populates="payment", uselist=False, lazy="select"
    )


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    plan: Mapped[SubscriptionPlanEnum] = mapped_column(
        SAEnum(SubscriptionPlanEnum), default=SubscriptionPlanEnum.basic, nullable=False
    )
    status: Mapped[SubscriptionStatusEnum] = mapped_column(
        SAEnum(SubscriptionStatusEnum),
        default=SubscriptionStatusEnum.active,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="subscriptions", lazy="select"
    )


class Badge(Base, TimestampMixin):
    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id"), unique=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="badges", lazy="select")
    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="badge", lazy="select"
    )


class Boost(Base, TimestampMixin):
    __tablename__ = "boosts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id"), unique=True, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="boosts", lazy="select")
    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="boost", lazy="select"
    )
