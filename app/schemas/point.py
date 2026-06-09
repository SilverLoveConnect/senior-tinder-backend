# 포인트 잔액 조회, 내역 조회, 포인트 사용 요청·응답 스키마
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.point import PointTypeEnum


class PointResponse(BaseModel):
    balance: int


class PointHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amount: int
    type: str
    description: str | None
    created_at: datetime


class PointHistoryResponse(BaseModel):
    history: list[PointHistoryItem]


class PointUseRequest(BaseModel):
    amount: int = Field(..., ge=1)
    type: PointTypeEnum
    description: str | None = None


class PointUseResponse(BaseModel):
    balance: int
    used: int
