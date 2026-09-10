# 차단 요청·응답 스키마
import uuid

from pydantic import BaseModel, ConfigDict, Field


class BlockResponse(BaseModel):
    message: str


class BlockUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # User.name(실명)을 nickname 자리에 매핑하고 있었다. 처리방침 제5조가
    # "실명과 휴대전화번호는 다른 회원에게 공개되지 않습니다"라고 명시하는데
    # 차단 목록만 실명을 내보내고 있었다(매칭 피드·대화 목록은 정상).
    nickname: str
    age: int
    region: str | None = None


class BlockListResponse(BaseModel):
    blocks: list[BlockUserInfo]
