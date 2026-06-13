import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.auth import SmsVerification
from app.models.user import User, UserProfile
from app.schemas.auth import RegisterRequest


def generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def send_sms_code(db: Session, phone: str) -> None:
    db.query(SmsVerification).filter(SmsVerification.phone == phone).delete()

    code = generate_code()
    verification = SmsVerification(
        phone=phone,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=3),
    )
    db.add(verification)
    db.commit()
    from app.services.sms import send_verification_sms

    # 테스트용 나중에 지울거
    print(f"{phone}->{code}")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="인증번호가 올바르지 않습니다.",
        )

    verification.is_used = True
    db.commit()
    return True


def register_user(db: Session, data: RegisterRequest) -> User:
    user = db.query(User).filter(User.phone == data.phone).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 가입된 회원입니다."
        )
    user = User(
        phone=data.phone,
        name=data.name,
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


def login_user(db: Session, phone: str) -> dict:
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="존재하지 않는 회원입니다."
        )
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
