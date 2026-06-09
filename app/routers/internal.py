# 내부 서비스(AI 서버 등) 간 통신 전용 라우터 — 인증 없음
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.internal import AIPhotoResultRequest, AIPhotoResultResponse
from app.services import internal as internal_service

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/ai/photo-result", response_model=AIPhotoResultResponse)
def ai_photo_result(
    body: AIPhotoResultRequest,
    db: Session = Depends(get_db),
) -> AIPhotoResultResponse:
    return internal_service.process_ai_photo_result(db, body)
