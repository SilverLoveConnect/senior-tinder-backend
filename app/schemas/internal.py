# 내부 서비스(AI 서버 등) 간 통신용 요청·응답 스키마
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AIPhotoResultRequest(BaseModel):
    user_id: uuid.UUID
    s3_url: str
    has_face: bool
    face_count: int
    face_confidence: float
    is_inappropriate: bool
    inappropriate_score: float
    quality_score: float
    analysis_status: str  # "success" | "error"
    error_message: str | None = None
    # 부적절 필터 모델이 아직 미학습이라 자동 승인/거부 대신 "사람이 봐야 함"을
    # 알려주는 값. True면 자동 승인하지 않고 검수 대기 상태로 둔다.
    needs_manual_review: bool = False


class AIPhotoResultResponse(BaseModel):
    message: str
    photo_approved: bool


class PendingPhotoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    s3_url: str
    created_at: datetime


class PendingPhotoListResponse(BaseModel):
    photos: list[PendingPhotoItem]
