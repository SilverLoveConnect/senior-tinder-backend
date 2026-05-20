# 모든 모델 임포트 — alembic autogenerate가 테이블을 감지하기 위해 필요
from app.models.manner import MannerHistory  # noqa: F401
from app.models.matching import Block, ChatRoom, Like, Match  # noqa: F401
from app.models.payment import Badge, Boost, Payment, Subscription  # noqa: F401
from app.models.point import Point, PointHistory  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.user import User, UserPhoto, UserProfile  # noqa: F401

__all__ = [
    "User",
    "UserProfile",
    "UserPhoto",
    "Like",
    "Match",
    "ChatRoom",
    "Block",
    "Report",
    "Point",
    "PointHistory",
    "Payment",
    "Subscription",
    "Badge",
    "Boost",
    "MannerHistory",
]
