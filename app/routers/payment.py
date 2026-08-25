# 포인트 충전, 구독 결제 엔드포인트
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentHistoryResponse,
    PointChargeRequest,
    PointChargeResponse,
    SubscriptionRequest,
    SubscriptionResponse,
)
from app.services import payment as payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


def require_payments_enabled() -> None:
    """결제가 꺼져 있으면 엔드포인트 자체를 없는 것처럼 취급한다.

    403이 아니라 404인 이유: 존재는 하지만 막혀 있다는 정보를 굳이 노출할
    이유가 없다. 조회(이력)와 구독 해지는 이미 결제한 사용자를 위해 열어 둔다.
    """
    if not settings.PAYMENTS_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


@router.post(
    "/points/charge",
    response_model=PointChargeResponse,
    dependencies=[Depends(require_payments_enabled)],
)
def charge_points(
    body: PointChargeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.charge_points(db, current_user, body)


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_payments_enabled)],
)
def subscribe(
    body: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.subscribe(db, current_user, body)


@router.delete("/subscriptions", response_model=SubscriptionResponse)
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.cancel_subscription(db, current_user)


@router.get("", response_model=PaymentHistoryResponse)
def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.get_payment_history(db, current_user)
