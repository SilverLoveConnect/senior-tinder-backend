"""창립 회원 대조 — 가입 시 사전 신청 행을 즉시 파기하고 창립 회원 여부만 남긴다.

처리방침 제5조: "같은 번호로 회원 가입하면 창립 회원 여부만 회원 정보에 기록한 뒤 즉시 파기".
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret")

from datetime import datetime, timedelta, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.pre_registration import PreRegistration  # noqa: E402
from app.models.user import GenderEnum, User  # noqa: E402
from app.services import auth as auth_service  # noqa: E402
from app.services.pre_registration import (  # noqa: E402
    FOUNDING_MEMBER_WINDOW,
    claim_founding_member,
)

PHONE = "01012345678"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    id_col = PreRegistration.__table__.c.id
    saved_default, id_col.server_default = id_col.server_default, None
    try:
        PreRegistration.__table__.create(engine)
    finally:
        id_col.server_default = saved_default
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


def _apply(db, phone=PHONE, notified_at=None):
    db.add(
        PreRegistration(
            name="홍길동",
            phone=phone,
            gender=GenderEnum.female,
            birth_year=1968,
            region="서울",
            privacy_consent=True,
            marketing_consent=True,
            notified_at=notified_at,
        )
    )
    db.commit()


def _count(db):
    return db.query(PreRegistration).count()


def test_applicant_before_launch_notice_is_founding_and_row_deleted(db):
    _apply(db)
    assert claim_founding_member(db, PHONE) is True
    db.commit()
    assert _count(db) == 0


def test_within_six_months_of_notice_is_founding(db):
    _apply(db, notified_at=datetime.now(timezone.utc) - timedelta(days=30))
    assert claim_founding_member(db, PHONE) is True


def test_after_window_not_founding_but_row_still_deleted(db):
    # 보유기간 배치가 늦게 돌아 행이 남아 있어도, 혜택은 주지 않고 정보는 지운다.
    _apply(db, notified_at=datetime.now(timezone.utc) - FOUNDING_MEMBER_WINDOW - timedelta(days=1))
    assert claim_founding_member(db, PHONE) is False
    db.commit()
    assert _count(db) == 0


def test_non_applicant_untouched(db):
    _apply(db, phone="01099998888")
    assert claim_founding_member(db, PHONE) is False
    db.commit()
    assert _count(db) == 1  # 다른 사람의 신청은 그대로


def test_phone_with_hyphens_still_matches(db):
    _apply(db)
    assert claim_founding_member(db, "010-1234-5678") is True


def test_no_commit_inside_claim(db):
    # 회원 생성과 한 트랜잭션이어야 한다 — 가입이 실패해 롤백되면 신청 정보도 남아야 한다.
    _apply(db)
    claim_founding_member(db, PHONE)
    db.rollback()
    assert _count(db) == 1


def test_register_user_stores_flag_from_claim():
    """register_user가 대조 결과를 회원 행에 넣고, 대조는 검증(SMS·금칙어)을 통과한 뒤에만 한다."""
    data = SimpleNamespace(
        phone=PHONE, code="123456", name="홍길동", nickname="길동",
        age=58, gender=GenderEnum.female, region="서울", marketing_consent=False,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None  # 미가입 번호
    added = []
    db.add.side_effect = added.append
    calls = []
    with patch.object(auth_service, "_ensure_sms_verified_for_register", lambda *a: calls.append("sms")), \
         patch.object(auth_service, "check_profile_text", lambda *a: calls.append("text")), \
         patch.object(auth_service, "claim_founding_member", lambda d, p: calls.append("claim") or True):
        auth_service.register_user(db, data)

    user = next(o for o in added if isinstance(o, User))
    assert user.is_founding_member is True
    assert calls.index("claim") > calls.index("sms")
    assert calls.index("claim") > max(i for i, c in enumerate(calls) if c == "text")
    db.commit.assert_called_once()
