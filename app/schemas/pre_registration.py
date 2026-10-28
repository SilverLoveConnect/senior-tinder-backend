# 사전 신청 요청·응답 스키마
from pydantic import BaseModel, Field

from app.models.user import GenderEnum


class PreRegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    phone: str = Field(min_length=10, max_length=20)
    gender: GenderEnum
    birth_year: int = Field(ge=1900, le=2100)
    region: str = Field(min_length=1, max_length=30)
    source: str | None = Field(default=None, max_length=30)
    privacy_consent: bool
    marketing_consent: bool = False


class PreRegistrationResponse(BaseModel):
    # 신청자 정보를 되돌려주지 않는다 — 다른 사람 번호로 조회하는 용도로 쓰일 수 없게
    ok: bool
    message: str


class PreRegistrationSummary(BaseModel):
    """성비·지역 모니터링용 집계 — 개인을 식별할 수 있는 값은 담지 않는다"""

    total: int
    marketing_consent: int
    by_gender: dict[str, int]
    by_region: dict[str, int]
    by_region_gender: dict[str, dict[str, int]]
    by_source: dict[str, int]
