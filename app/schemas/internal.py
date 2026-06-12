# 내부 서비스(AI 서버 등) 간 통신용 요청·응답 스키마
import uuid

from pydantic import BaseModel


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


class AIPhotoResultResponse(BaseModel):
    message: str
    photo_approved: bool
