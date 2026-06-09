from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.users import UpdateProfileRequest, UserProfileResponse
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return users_service.get_profile(current_user)


@router.put("/me", response_model=UserProfileResponse)
def update_me(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return users_service.update_profile(db, current_user, body)
