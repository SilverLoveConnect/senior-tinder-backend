# 유저 프로필 조회 및 수정 요청·응답 스키마
import uuid

from pydantic import BaseModel, ConfigDict, Field


class FcmTokenRequest(BaseModel):
    fcm_token: str


class UpdateSettingsRequest(BaseModel):
    # bool → bool | None은 완화라 기존 앱 요청이 그대로 통과한다
    chat_push_enabled: bool | None = None
    marketing_consent: bool | None = None


class UpdateSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chat_push_enabled: bool
    marketing_consent: bool


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=20)
    nickname: str | None = Field(default=None, min_length=2, max_length=20)
    region: str | None = None
    bio: str | None = None
    life_story: str | None = None
    interests: list[str] | None = None
    height: int | None = Field(default=None, ge=100, le=250)
    job: str | None = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str
    name: str
    nickname: str
    age: int
    gender: str | None = None
    region: str | None = None
    bio: str | None = None
    life_story: str | None = None
    interests: list[str] | None = None
    height: int | None = None
    job: str | None = None
    trust_score: int = 50
    trust_grade: str = "normal"
    is_verified: bool = False
    photos: list[str] = []
    # 승인 대기·거부된 사진. 이 값이 없으면 사용자는 자기가 올린 사진이
    # 왜 프로필에 안 뜨는지 알 수 없고, 지울 수도 없다(업로드 한도만 찬다).
    pending_photos: list[str] = []
    rejected_photos: list[str] = []
