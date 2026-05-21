# 사용자, 프로필, 사진 모델
import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.manner import MannerHistory
    from app.models.matching import Block, Like, Match
    from app.models.payment import Badge, Boost, Payment, Subscription
    from app.models.point import Point, PointHistory
    from app.models.report import Report


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"


class MannerGradeEnum(str, enum.Enum):
    gold = "gold"
    silver = "silver"
    normal = "normal"
    warning = "warning"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    phone: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[GenderEnum] = mapped_column(SAEnum(GenderEnum), nullable=False)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False, lazy="select"
    )
    photos: Mapped[list["UserPhoto"]] = relationship(
        "UserPhoto", back_populates="user", lazy="select"
    )
    likes_sent: Mapped[list["Like"]] = relationship(
        "Like",
        foreign_keys="Like.from_user_id",
        back_populates="from_user",
        lazy="select",
    )
    likes_received: Mapped[list["Like"]] = relationship(
        "Like", foreign_keys="Like.to_user_id", back_populates="to_user", lazy="select"
    )
    matches_as_user1: Mapped[list["Match"]] = relationship(
        "Match", foreign_keys="Match.user1_id", back_populates="user1", lazy="select"
    )
    matches_as_user2: Mapped[list["Match"]] = relationship(
        "Match", foreign_keys="Match.user2_id", back_populates="user2", lazy="select"
    )
    blocks_given: Mapped[list["Block"]] = relationship(
        "Block",
        foreign_keys="Block.blocker_id",
        back_populates="blocker",
        lazy="select",
    )
    blocks_received: Mapped[list["Block"]] = relationship(
        "Block",
        foreign_keys="Block.blocked_id",
        back_populates="blocked",
        lazy="select",
    )
    reports_sent: Mapped[list["Report"]] = relationship(
        "Report",
        foreign_keys="Report.reporter_id",
        back_populates="reporter",
        lazy="select",
    )
    reports_received: Mapped[list["Report"]] = relationship(
        "Report",
        foreign_keys="Report.reported_id",
        back_populates="reported",
        lazy="select",
    )
    point: Mapped["Point"] = relationship(
        "Point", back_populates="user", uselist=False, lazy="select"
    )
    point_histories: Mapped[list["PointHistory"]] = relationship(
        "PointHistory", back_populates="user", lazy="select"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="user", lazy="select"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", lazy="select"
    )
    badges: Mapped[list["Badge"]] = relationship(
        "Badge", back_populates="user", lazy="select"
    )
    boosts: Mapped[list["Boost"]] = relationship(
        "Boost", back_populates="user", lazy="select"
    )
    manner_histories: Mapped[list["MannerHistory"]] = relationship(
        "MannerHistory", back_populates="user", lazy="select"
    )


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    life_story: Mapped[str | None] = mapped_column(Text, nullable=True)
    interests: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    manner_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    manner_grade: Mapped[MannerGradeEnum] = mapped_column(
        SAEnum(MannerGradeEnum), default=MannerGradeEnum.normal, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="profile", lazy="select")


class UserPhoto(Base, TimestampMixin):
    __tablename__ = "user_photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    s3_url: Mapped[str] = mapped_column(String, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="photos", lazy="select")
