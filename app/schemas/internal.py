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
    analysis_status: str  # "success" | "error"  ← AI 서버 기준으로 통일
    photo_uploaded: bool = True
    # face_detected 제거 — AI 서버는 has_face 필드로 전송 (위의 has_face 사용)


class AIPhotoResultResponse(BaseModel):
    message: str
    photo_approved: bool
