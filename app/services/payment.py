# 포트원 V1 결제 검증, 포인트 충전, 구독 처리 서비스
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.payment import (
    Payment,
    PaymentStatusEnum,
    PaymentTypeEnum,
    Subscription,
    SubscriptionStatusEnum,
)
from app.models.point import Point, PointHistory, PointTypeEnum
from app.models.user import User
from app.schemas.payment import PointChargeRequest, SubscriptionRequest

POINT_PACKAGES = {
    "basic": {"amount": 1000, "points": 100},
    "standard": {"amount": 5000, "points": 550},
    "premium": {"amount": 10000, "points": 1200},
    "vip": {"amount": 30000, "points": 4000},
}

SUBSCRIPTION_PLANS = {
    "basic": {"amount": 9900, "duration_days": 30},
    "gold": {"amount": 29900, "duration_days": 30},
}

PORTONE_BASE_URL = "https://api.iamport.kr"


def _get_portone_token() -> str:
    res = httpx.post(
        f"{PORTONE_BASE_URL}/users/getToken",
        json={
            "imp_key": settings.PORTONE_IMP_KEY,
            "imp_secret": settings.PORTONE_IMP_SECRET,
        },
        timeout=5,
    )
    body = res.json()
    if res.status_code != 200 or body.get("code") != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="포트원 토큰 발급에 실패했습니다.",
        )
    return body["response"]["access_token"]


def _verify_portone_payment(imp_uid: str) -> dict:
    token = _get_portone_token()
    res = httpx.get(
        f"{PORTONE_BASE_URL}/payments/{imp_uid}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    body = res.json()
    if res.status_code != 200 or body.get("code") != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="결제 검증에 실패했습니다."
        )

    payment_info = body["response"]
    if payment_info.get("status") != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="결제가 완료되지 않았습니다.",
        )
    return payment_info


def _check_duplicate_payment(db: Session, imp_uid: str) -> None:
    if db.query(Payment).filter(Payment.imp_uid == imp_uid).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리된 결제입니다.",
        )


def charge_points(db: Session, current_user: User, data: PointChargeRequest) -> dict:
    package = POINT_PACKAGES.get(data.package)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 패키지입니다.",
        )

    payment_info = _verify_portone_payment(data.imp_uid)
    if payment_info["amount"] != package["amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="결제금액 불일치"
        )

    _check_duplicate_payment(db, data.imp_uid)

    payment = Payment(
        user_id=current_user.id,
        imp_uid=data.imp_uid,
        amount=payment_info["amount"],
        type=PaymentTypeEnum.point,
        status=PaymentStatusEnum.paid,
    )
    db.add(payment)

    point = db.query(Point).filter(Point.user_id == current_user.id).first()
    if not point:
        point = Point(user_id=current_user.id, balance=0)
        db.add(point)

    point.balance += package["points"]
    db.add(
        PointHistory(
            user_id=current_user.id,
            amount=package["points"],
            type=PointTypeEnum.charge,
            description=f"{data.package} 패키지 충전",
        )
    )

    db.commit()
    return {"balance": point.balance, "charged_points": package["points"]}


def subscribe(db: Session, current_user: User, data: SubscriptionRequest) -> dict:
    plan_info = SUBSCRIPTION_PLANS.get(data.plan.value)
    if not plan_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 구독 플랜입니다.",
        )

    payment_info = _verify_portone_payment(data.imp_uid)
    if payment_info["amount"] != plan_info["amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="결제금액 불일치"
        )

    _check_duplicate_payment(db, data.imp_uid)

    payment = Payment(
        user_id=current_user.id,
        imp_uid=data.imp_uid,
        amount=payment_info["amount"],
        type=PaymentTypeEnum.subscription,
        status=PaymentStatusEnum.paid,
    )
    db.add(payment)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=plan_info["duration_days"]
    )
    subscription = (
        db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    )
    if subscription:
        subscription.plan = data.plan
        subscription.status = SubscriptionStatusEnum.active
        subscription.expires_at = expires_at
    else:
        subscription = Subscription(
            user_id=current_user.id,
            plan=data.plan,
            status=SubscriptionStatusEnum.active,
            expires_at=expires_at,
        )
        db.add(subscription)

    db.commit()
    return {"plan": subscription.plan, "expires_at": subscription.expires_at, "is_active": True}
