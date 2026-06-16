# 유저 프로필 조회 및 수정 요청·응답 스키마
import uuid

from pydantic import BaseModel, ConfigDict, Field


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
