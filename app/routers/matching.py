# 매칭 추천 유저 목록 조회 라우터
# GET /matching — 커서 기반 페이지네이션으로 추천 유저를 반환한다.
# 차단·이미 좋아요한 유저를 제외하고, 나이·지역 필터를 지원한다.
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.matching import MatchingListResponse
from app.services import matching as matching_service

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("", response_model=MatchingListResponse)
def get_matching(
    cursor: str | None = Query(default=None, description="커서 (마지막으로 받은 유저 ID)"),
    size: int = Query(default=10, ge=1, le=100, description="한 번에 조회할 유저 수"),
    min_age: int | None = Query(default=None, ge=0, description="최소 나이 필터"),
    max_age: int | None = Query(default=None, ge=0, description="최대 나이 필터"),
    region: str | None = Query(default=None, description="지역 필터"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchingListResponse:
    result = matching_service.get_matching_users(
        db=db,
        current_user=current_user,
        cursor=cursor,
        size=size,
        min_age=min_age,
        max_age=max_age,
        region=region,
    )
    return MatchingListResponse(**result)
