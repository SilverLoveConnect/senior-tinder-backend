from sqlalchemy.orm import Session
from app.models.user import User, UserPhoto
from app.schemas.users import UpdateProfileRequest
from app.services.manner import update_trust_score
from app.models.manner import MannerFactorEnum


def get_profile(user: User) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name,
        "nickname": user.nickname or user.name,
        "age": user.age,
        "gender": user.gender,
        "region": user.region,
        "bio": user.profile.bio if user.profile else None,
        "life_story": user.profile.life_story if user.profile else None,
        "interests": user.profile.interests if user.profile else None,
        "height": user.profile.height if user.profile else None,
        "job": user.profile.job if user.profile else None,
        "trust_score": user.profile.trust_score if user.profile else 50,
        "trust_grade": user.profile.trust_grade if user.profile else "normal",
        "is_verified": user.profile.is_verified if user.profile else False,
        "photos": [p.s3_url for p in user.photos if p.is_approved],
    }


def update_profile(db: Session, user: User, data: UpdateProfileRequest) -> dict:
    if data.name is not None:
        user.name = data.name
    if data.nickname is not None:
        user.nickname = data.nickname
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

        photo_count = len(user.photos)
        bio_length = len(user.profile.bio or "")

        if photo_count >= 3 or bio_length >= 100:
            update_trust_score(
                db=db,
                user=user,
                factor=MannerFactorEnum.profile,
                delta=10,
                reason="프로필 완성도 달성 (사진 3장+, 자기소개 100자+)",
            )
    db.commit()
    db.refresh(user)
    return get_profile(user)


def delete_account(db: Session, user: User) -> None:
    """회원 탈퇴 — 소프트 삭제.

    - is_active=False 처리 (재가입 시 같은 번호를 다시 쓸 수 있도록 phone은 익명화)
    - name/nickname 익명화, fcm_token 제거
    - 등록된 사진 전부 삭제
    """
    user.is_active = False
    user.name = "탈퇴한 사용자"
    user.nickname = "탈퇴한 사용자"
    user.phone = f"deleted:{user.id}"
    user.fcm_token = None

    db.query(UserPhoto).filter(UserPhoto.user_id == user.id).delete()

    db.commit()
