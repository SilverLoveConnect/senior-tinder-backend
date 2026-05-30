# 차단 관련 라우터
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.block import BlockListResponse, BlockResponse
from app.services import block as block_service

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.post("/{user_id}", response_model=BlockResponse)
def create_block(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlockResponse:
    return block_service.create_block(db, current_user, user_id)


@router.delete("/{user_id}", response_model=BlockResponse)
def delete_block(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlockResponse:
    return block_service.delete_block(db, current_user, user_id)


@router.get("", response_model=BlockListResponse)
def get_blocks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlockListResponse:
    return block_service.get_blocks(db, current_user)
