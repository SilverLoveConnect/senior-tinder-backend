"""Android 출시 전 QA(2026-11-19) P1-1·P1-2·P2-1·P2-2 가드 테스트.

검사들은 전부 DB 조회 결과(대상 회원) 하나만 보고 판단하므로, 매칭 테이블 전체를
SQLite에 만들지 않고 "첫 조회에 대상 회원을 돌려주는" 가짜 세션으로 확인한다.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret")

import re  # noqa: E402
import uuid  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.routers.chat import MESSAGE_MAX_LENGTH, SendMessageRequest  # noqa: E402
from app.routers.users import delete_fcm_token  # noqa: E402
from app.services import pre_registration  # noqa: E402
from app.services.block import create_block  # noqa: E402
from app.services.matching import like_user  # noqa: E402


def _user(**kw):
    base = dict(id=uuid.uuid4(), is_banned=False, is_active=True, fcm_token=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _db_returning(target):
    """db.query(...).filter(...).first() 가 처음에 target을 돌려주는 가짜 세션."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = target
    return db


# --- P1-1 자기 자신 좋아요·차단 ---------------------------------------------

def test_like_self_rejected_before_any_write():
    me = _user()
    db = _db_returning(me)
    with pytest.raises(HTTPException) as e:
        like_user(db, me, str(me.id))
    assert e.value.status_code == 400
    db.add.assert_not_called()


def test_block_self_rejected():
    me = _user()
    db = _db_returning(me)
    with pytest.raises(HTTPException) as e:
        create_block(db, me, str(me.id))
    assert e.value.status_code == 400
    db.add.assert_not_called()


# --- P2-2 정지·탈퇴 회원에게 좋아요 ---------------------------------------

@pytest.mark.parametrize("target", [_user(is_banned=True), _user(is_active=False)])
def test_like_banned_or_inactive_is_404(target):
    db = _db_returning(target)
    with pytest.raises(HTTPException) as e:
        like_user(db, _user(), str(target.id))
    assert e.value.status_code == 404
    db.add.assert_not_called()


def test_like_missing_user_is_404():
    with pytest.raises(HTTPException) as e:
        like_user(_db_returning(None), _user(), str(uuid.uuid4()))
    assert e.value.status_code == 404


# --- P2-1 빈 메시지·길이 제한 ----------------------------------------------

@pytest.mark.parametrize("content", ["", "   ", "\n\t", "x" * (MESSAGE_MAX_LENGTH + 1)])
def test_message_invalid_content_rejected(content):
    with pytest.raises(ValidationError):
        SendMessageRequest(content=content)


@pytest.mark.parametrize("content", ["안녕하세요", " 앞뒤 공백 ", "x" * MESSAGE_MAX_LENGTH])
def test_message_valid_content_kept_as_is(content):
    assert SendMessageRequest(content=content).content == content


# --- P1-2 푸시 토큰 삭제 -----------------------------------------------------

def test_delete_fcm_token_clears_and_commits():
    me = _user(fcm_token="ExponentPushToken[abc]")
    db = MagicMock()
    delete_fcm_token(current_user=me, db=db)
    assert me.fcm_token is None
    db.commit.assert_called_once()


def test_delete_fcm_token_idempotent_without_token():
    me = _user(fcm_token=None)
    db = MagicMock()
    delete_fcm_token(current_user=me, db=db)
    db.commit.assert_not_called()


# --- 사전 신청 번호 규칙 = 앱 가입 규칙 ----------------------------------

def test_pre_registration_phone_rule_matches_signup_rule():
    signup = re.compile(r"^010[0-9]{8}$")  # schemas/auth.py _phone_field
    for phone in ["01012345678", "0111234567", "01112345678", "0161234567", "0101234567"]:
        assert bool(pre_registration.PHONE_RE.match(phone)) == bool(signup.match(phone)), phone
