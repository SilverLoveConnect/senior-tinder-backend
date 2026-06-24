# 포인트 충전, 구독 결제 엔드포인트
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.payment import (
    PointChargeRequest,
    PointChargeResponse,
    SubscriptionRequest,
    SubscriptionResponse,
)
from app.services import payment as payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/points/charge", response_model=PointChargeResponse)
def charge_points(
    body: PointChargeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.charge_points(db, current_user, body)


@router.post("/subscriptions", response_model=SubscriptionResponse)
def subscribe(
    body: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.subscribe(db, current_user, body)
