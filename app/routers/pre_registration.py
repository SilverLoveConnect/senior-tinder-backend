# 출시 전 사전 신청 라우터 — 로그인 없이 호출되는 공개 엔드포인트
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, verify_internal_token
from app.schemas.pre_registration import (
    PreRegistrationRequest,
    PreRegistrationResponse,
    PreRegistrationSummary,
)
from app.services import pre_registration as pre_registration_service

router = APIRouter(tags=["pre-registrations"])


def _client_ip(request: Request) -> str | None:
    # Railway 프록시 뒤라 실제 IP는 X-Forwarded-For 첫 값이다
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/pre-registrations", response_model=PreRegistrationResponse)
def create_pre_registration(
    body: PreRegistrationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PreRegistrationResponse:
    return pre_registration_service.register(db, body, _client_ip(request))


@router.get(
    "/internal/pre-registrations/summary",
    response_model=PreRegistrationSummary,
    dependencies=[Depends(verify_internal_token)],
)
def get_pre_registration_summary(db: Session = Depends(get_db)) -> PreRegistrationSummary:
    """성별·지역·유입경로 집계 숫자만 — 명단은 내보내지 않는다"""
    return pre_registration_service.summary(db)
