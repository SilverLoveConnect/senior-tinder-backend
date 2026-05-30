# 신고 요청·응답 스키마
import uuid

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    reported_id: uuid.UUID
    reason: str = Field(min_length=5, max_length=500)


class ReportResponse(BaseModel):
    message: str
