# 출시 전 사전 신청 모델 — 앱 회원(users)과 분리된 별도 명단
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.user import GenderEnum


class PreRegistration(Base, TimestampMixin):
    """
    사전 신청 페이지(org 사이트 pre-register.html)로 들어온 출시 알림 신청.

    회원 가입이 아니다 — 로그인·매칭에 쓰지 않고, 출시 안내와 지역별 오픈 순서
    결정에만 쓴다. 보유기간은 출시 안내 후 6개월(동의서 고지 사항).
    """

    __tablename__ = "pre_registrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    # 숫자만 저장한다. 같은 번호로 다시 신청하면 새 행 대신 기존 행을 갱신한다.
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    gender: Mapped[GenderEnum] = mapped_column(SAEnum(GenderEnum), nullable=False)
    birth_year: Mapped[int] = mapped_column(Integer, nullable=False)
    # "서울" / "경기 수원시" / "기타"
    region: Mapped[str] = mapped_column(String(30), nullable=False)
    # 유입 경로(?from=band 등) — 어느 채널이 효과 있는지 집계용
    source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    privacy_consent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # 정보통신망법 제50조 — 출시 알림 문자는 이 값이 true인 사람에게만 보낸다
    marketing_consent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
