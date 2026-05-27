# 매칭 추천 유저 목록 조회 요청·응답 스키마
import uuid

from pydantic import BaseModel, ConfigDict


class MatchingUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    age: int
    region: str | None = None
    bio: str | None = None
    interests: list[str] | None = None
    manner_score: int = 50
    manner_grade: str = "normal"
    is_verified: bool = False


class MatchingListResponse(BaseModel):
    users: list[MatchingUserResponse]
    next_cursor: str | None
    has_next: bool
