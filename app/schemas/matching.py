# 매칭 추천 유저 목록 조회 요청·응답 스키마
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MatchingUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    age: int
    region: str | None = None
    bio: str | None = None
    interests: list[str] | None = None
    trust_score: int = 50
    trust_grade: str = "normal"
    is_verified: bool = False
    photos: list[str] = []


class MatchingListResponse(BaseModel):
    users: list[MatchingUserResponse]
    next_cursor: str | None
    has_next: bool


class LikeResponse(BaseModel):
    is_matched: bool
    match_id: str | None


class MatchUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    age: int
    region: str | None
    trust_grade: str


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: uuid.UUID
    user: MatchUserInfo
    matched_at: datetime
    chat_room_id: uuid.UUID


class MatchListResponse(BaseModel):
    matches: list[MatchResponse]
