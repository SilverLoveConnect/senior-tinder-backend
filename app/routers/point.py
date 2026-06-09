# 포인트 잔액 조회, 내역 조회, 포인트 사용 라우터
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.point import PointHistoryResponse, PointResponse, PointUseRequest, PointUseResponse
from app.services import point as point_service

router = APIRouter(prefix="/points", tags=["points"])


@router.get("", response_model=PointResponse)
def get_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PointResponse:
    return point_service.get_balance(db, current_user)


@router.get("/history", response_model=PointHistoryResponse)
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PointHistoryResponse:
    return point_service.get_history(db, current_user)


@router.post("/use", response_model=PointUseResponse)
def use_points(
    body: PointUseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PointUseResponse:
    return point_service.use_points(db, current_user, body)
