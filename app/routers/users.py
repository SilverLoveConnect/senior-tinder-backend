# 유저 관련 라우터 — 현재 로그인한 유저 정보 조회
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import RegisterResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=RegisterResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
