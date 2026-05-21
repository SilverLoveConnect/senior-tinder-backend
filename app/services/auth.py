import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token
from app.models.auth import SmsVerification
from app.models.user import User
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
    # (TODO: SOLAPI 연동) 추후에 해야함!!!!!!
    print(f"[SMS] {phone} → 인증번호: {code}")


from fastapi import HTTPException, status


def verify_sms_code(db: Session, phone: str, code: str) -> bool:

    verification = (
        db.query(SmsVerification)
        .filter(SmsVerification.phone == phone, SmsVerification.is_used == False)
        .first()
    )

    if not verification:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="???")

    if datetime.now(timezone.utc) > verification.expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="???")

    if verification.code != code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="???")

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
