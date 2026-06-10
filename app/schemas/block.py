# 차단 요청·응답 스키마
import uuid

from pydantic import BaseModel, ConfigDict, Field


class BlockResponse(BaseModel):
    message: str


class BlockUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str = Field(validation_alias="name")
    age: int
    region: str | None = None


class BlockListResponse(BaseModel):
    blocks: list[BlockUserInfo]
