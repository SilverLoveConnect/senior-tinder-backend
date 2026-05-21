# SMS 인증, 회원가입, 로그인 엔드포인트
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    SmsSendRequest,
    SmsSendResponse,
    SmsVerifyRequest,
    SmsVerifyResponse,
    TokenResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/sms/send", response_model=SmsSendResponse)
def send_sms(body: SmsSendRequest, db: Session = Depends(get_db)):
    auth_service.send_sms_code(db, body.phone)
    return SmsSendResponse(message="인증번호가 발송되었습니다.")


@router.post("/sms/verify", response_model=SmsVerifyResponse)
def verify_sms(body: SmsVerifyRequest, db: Session = Depends(get_db)):
    is_verified = auth_service.verify_sms_code(db, body.phone, body.code)
    return SmsVerifyResponse(message="인증이 완료되었습니다.", is_verified=is_verified)


@router.post("/register", response_model=RegisterResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, body)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    auth_service.verify_sms_code(db, body.phone, body.code)
    tokens = auth_service.login_user(db, body.phone)
    return TokenResponse(**tokens)
