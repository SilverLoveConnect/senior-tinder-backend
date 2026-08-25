# 내부 서비스(AI 서버 등) 간 통신 전용 라우터
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, verify_internal_token
from app.schemas.internal import (
    AIPhotoResultRequest,
    AIPhotoResultResponse,
    PendingPhotoListResponse,
    PhotoReviewRequest,
    PhotoReviewResponse,
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


@router.post(
    "/photos/{photo_id}/review",
    response_model=PhotoReviewResponse,
    dependencies=[Depends(verify_internal_token)],
)
def review_photo(
    photo_id: uuid.UUID,
    body: PhotoReviewRequest,
    db: Session = Depends(get_db),
) -> PhotoReviewResponse:
    """
    검수 대기 사진 승인/거부 (관리자용).

    이 엔드포인트가 없으면 needs_manual_review로 pending에 들어간 사진이
    빠져나올 방법이 없다 — 목록 조회만 있고 처리 수단이 없었다.
    """
    return internal_service.review_photo(db, photo_id, body.approve)
