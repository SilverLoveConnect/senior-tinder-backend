# SMS 인증 및 회원가입/로그인 요청·응답 스키마
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.models.user import GenderEnum

_phone_field = Field(pattern=r"^010[0-9]{8}$")


# TODO: 배포 전 examples 제거
class SmsSendRequest(BaseModel):
    phone: str = Field(pattern=r"^010[0-9]{8}$", examples=["01011480193"])


class SmsSendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str


class SmsVerifyRequest(BaseModel):
    phone: str = _phone_field
    code: str = Field(min_length=6, max_length=6)


class SmsVerifyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    is_verified: bool


class RegisterRequest(BaseModel):
    phone: str = _phone_field
    name: str = Field(min_length=2, max_length=20)
    age: int = Field(ge=50, le=100)
    gender: GenderEnum
    region: str | None = None


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str
    name: str


class LoginRequest(BaseModel):
    phone: str = Field(pattern=r"^010[0-9]{8}$", examples=["01011480193"])
    code: str = Field(min_length=6, max_length=6, examples=["123456"])


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    refresh_token: str | None = None  # 선택으로 변경
    token_type: str = "bearer"
