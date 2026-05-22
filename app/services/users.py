from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.users import UpdateProfileRequest


def get_profile(user: User) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name,
        "age": user.age,
        "gender": user.gender,
        "region": user.region,
        "bio": user.profile.bio if user.profile else None,
        "life_story": user.profile.life_story if user.profile else None,
        "interests": user.profile.interests if user.profile else None,
        "height": user.profile.height if user.profile else None,
        "job": user.profile.job if user.profile else None,
        "manner_score": user.profile.manner_score if user.profile else 50,
        "manner_grade": user.profile.manner_grade if user.profile else "normal",
        "is_verified": user.profile.is_verified if user.profile else False,
    }


def update_profile(db: Session, user: User, data: UpdateProfileRequest) -> dict:
    if data.name is not None:
        user.name = data.name
    if data.region is not None:
        user.region = data.region

    if user.profile:
        if data.bio is not None:
            user.profile.bio = data.bio
        if data.life_story is not None:
            user.profile.life_story = data.life_story
        if data.interests is not None:
            user.profile.interests = data.interests
        if data.height is not None:
            user.profile.height = data.height
        if data.job is not None:
            user.profile.job = data.job

    db.commit()
    db.refresh(user)
    return get_profile(user)
