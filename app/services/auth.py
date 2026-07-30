import random
import re
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.auth import SmsSendLog, SmsVerification
from app.models.user import User, UserProfile
from app.schemas.auth import RegisterRequest

MAX_VERIFY_ATTEMPTS = 5
SEND_RATE_LIMIT_INTERVAL = timedelta(minutes=1)
SEND_RATE_LIMIT_DAILY_MAX = 10
# register_user에서 "/auth/verify로 이미 인증을 마쳤는지"를 확인할 때 허용하는 유효 기간.
# verify_sms_code를 그대로 재호출하면 is_used=True라서 재검증이 항상 실패하므로,
# 최근에 같은 phone+code로 "성공 소비"된 인증 기록이 있는지만 확인한다.
REGISTER_SMS_VERIFY_WINDOW = timedelta(minutes=15)


def generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def _is_review_phone(phone: str) -> bool:
    """심사관(App Store/Play Store) 검수용 전화번호인지 확인. 두 값이 모두 설정된 경우에만 활성화.
    .env의 REVIEW_TEST_PHONE에 하이픈 등 구분자가 섞여 있어도 안전하게 매칭되도록 숫자만 비교."""
    review_phone = settings.REVIEW_TEST_PHONE
    return bool(review_phone) and _normalize_phone(phone) == _normalize_phone(review_phone)


def send_sms_code(db: Session, phone: str) -> None:
    if _is_review_phone(phone):
        # 심사용 번호: rate limit/실제 SMS 발송 없이 고정 인증코드로 대체
        db.query(SmsVerification).filter(SmsVerification.phone == phone).delete()
        verification = SmsVerification(
            phone=phone,
            code=settings.REVIEW_TEST_CODE,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(verification)
        db.commit()
        return

    now = datetime.now(timezone.utc)

    recent_send_exists = (
        db.query(SmsSendLog)
        .filter(
            SmsSendLog.phone == phone,
            SmsSendLog.created_at >= now - SEND_RATE_LIMIT_INTERVAL,
        )
        .first()
        is not None
    )
    if recent_send_exists:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="잠시 후 다시 시도해주세요. (1분에 1회만 요청할 수 있습니다)",
        )

    daily_send_count = (
        db.query(SmsSendLog)
        .filter(
            SmsSendLog.phone == phone,
            SmsSendLog.created_at >= now - timedelta(days=1),
        )
        .count()
    )
    if daily_send_count >= SEND_RATE_LIMIT_DAILY_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="일일 인증번호 요청 횟수를 초과했습니다. 내일 다시 시도해주세요.",
        )

    db.query(SmsVerification).filter(SmsVerification.phone == phone).delete()

    code = generate_code()
    verification = SmsVerification(
        phone=phone,
        code=code,
        expires_at=now + timedelta(minutes=3),
    )
    db.add(verification)
    db.add(SmsSendLog(phone=phone))
    db.commit()
    from app.services.sms import send_verification_sms

    send_verification_sms(phone, code)


def verify_sms_code(db: Session, phone: str, code: str) -> bool:

    verification = (
        db.query(SmsVerification)
        .filter(SmsVerification.phone == phone, SmsVerification.is_used == False)
        .first()
    )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="인증번호를 먼저 요청해주세요",
        )

    if datetime.now(timezone.utc) > verification.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="인증번호가 만료됐습니다."
        )

    if verification.code != code:
        verification.attempt_count += 1
        if verification.attempt_count >= MAX_VERIFY_ATTEMPTS:
            verification.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증 시도 횟수를 초과했습니다. 인증번호를 다시 요청해주세요.",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="인증번호가 올바르지 않습니다.",
        )

    verification.is_used = True
    db.commit()
    return True


def _ensure_sms_verified_for_register(db: Session, phone: str, code: str) -> None:
    """register 직전 SMS 인증 여부를 확인한다.

    프론트는 /auth/verify(인증 확인 화면)에서 이미 verify_sms_code를 호출해
    SmsVerification.is_used=True로 코드를 소비한다. 여기서 verify_sms_code를
    그대로 다시 호출하면 "이미 사용됨" 처리로 항상 실패하므로, 대신 phone+code가
    일치하고 최근 REGISTER_SMS_VERIFY_WINDOW 이내에 is_used=True로 소비된
    인증 기록이 존재하는지만 확인한다.
    """
    verification = (
        db.query(SmsVerification)
        .filter(
            SmsVerification.phone == phone,
            SmsVerification.code == code,
            SmsVerification.is_used == True,
        )
        .order_by(SmsVerification.created_at.desc())
        .first()
    )
    if (
        not verification
        or verification.created_at
        < datetime.now(timezone.utc) - REGISTER_SMS_VERIFY_WINDOW
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMS 인증을 먼저 완료해주세요.",
        )


def register_user(db: Session, data: RegisterRequest) -> User:
    user = db.query(User).filter(User.phone == data.phone).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 가입된 회원입니다."
        )

    _ensure_sms_verified_for_register(db, data.phone, data.code)

    user = User(
        phone=data.phone,
        name=data.name,
        nickname=data.nickname,
        age=data.age,
        gender=data.gender,
        region=data.region,
    )
    db.add(user)
    db.flush()

    profile = UserProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, phone: str, code: str) -> dict:
    # 1. 유저 존재 먼저 확인 (코드 소비 없이)
    # 신규 유저면 코드를 소비하지 않고 400 반환 → 회원가입 후 동일 코드로 재로그인 가능
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="존재하지 않는 회원입니다."
        )
    # 2. 유저가 있을 때만 코드 검증 (여기서 is_used = True)
    verify_sms_code(db, phone, code)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다."
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token이 아닙니다."
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token이 아닙니다."
        )
    user = db.query(User).filter(User.id == subject).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="등록된 회원이 아닙니다."
        )

    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token}
