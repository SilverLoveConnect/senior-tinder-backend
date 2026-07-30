# 내부 서비스(AI 서버 등) 간 통신 전용 라우터
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, verify_internal_token
from app.schemas.internal import (
    AIPhotoResultRequest,
    AIPhotoResultResponse,
    PendingPhotoListResponse,
)
from app.services import internal as internal_service

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post(
    "/ai/photo-result",
    response_model=AIPhotoResultResponse,
    dependencies=[Depends(verify_internal_token)],
)
def ai_photo_result(
    body: AIPhotoResultRequest,
    db: Session = Depends(get_db),
) -> AIPhotoResultResponse:
    return internal_service.process_ai_photo_result(db, body)


@router.get(
    "/photos/pending",
    response_model=PendingPhotoListResponse,
    dependencies=[Depends(verify_internal_token)],
)
def get_pending_photos(db: Session = Depends(get_db)) -> PendingPhotoListResponse:
    """관리자 검수 대기 중인 사진 목록 (정식 어드민 UI는 별도 스코프)"""
    return internal_service.get_pending_photos(db)
