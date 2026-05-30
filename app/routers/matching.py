from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.matching import MatchingListResponse, LikeResponse, MatchListResponse
from app.services import matching as matching_service

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("", response_model=MatchingListResponse)
def get_matching(
    cursor: str | None = Query(
        default=None, description="커서 (마지막으로 받은 유저 ID)"
    ),
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


@router.post("/like/{user_id}", response_model=LikeResponse)
def like_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return matching_service.like_user(db, current_user, user_id)


@router.get("/matches", response_model=MatchListResponse)
def get_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return matching_service.get_matches(db, current_user)
