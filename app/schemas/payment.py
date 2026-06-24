# 포인트 충전 및 구독 결제 요청·응답 스키마
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.payment import SubscriptionPlanEnum


class PointChargeRequest(BaseModel):
    imp_uid: str  # 포트원 결제번호
    package: str  # "basic" | "standard" | "premium" | "vip"


class PointChargeResponse(BaseModel):
    balance: int  # 충전 후 잔액
    charged_points: int  # 지급된 포인트


class SubscriptionRequest(BaseModel):
    imp_uid: str
    plan: SubscriptionPlanEnum


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: SubscriptionPlanEnum
    expires_at: datetime
    is_active: bool
