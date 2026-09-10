from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.matching import ChatRoom, Match
from app.models.user import PhotoReviewStatusEnum, User, UserPhoto
from app.services.s3 import delete_photo_objects
from app.schemas.users import UpdateProfileRequest, UpdateSettingsRequest
from app.services.manner import has_factor_history, update_trust_score
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
        "pending_photos": [
            p.s3_url
            for p in user.photos
            if not p.is_approved and p.review_status == PhotoReviewStatusEnum.pending
        ],
        "rejected_photos": [
            p.s3_url
            for p in user.photos
            if p.review_status == PhotoReviewStatusEnum.rejected
        ],
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

        # 프로필 완성 가점은 계정당 한 번뿐이다. 가드가 없으면 저장 버튼을
        # 누를 때마다 +10이 누적돼 신뢰점수를 무한히 올릴 수 있다.
        if (photo_count >= 3 or bio_length >= 100) and not has_factor_history(
            db, user, MannerFactorEnum.profile
        ):
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
    - 등록된 사진 전부 삭제 (DB 행 + S3 원본)
    - 참여 중이던 채팅방 비활성화
    """
    user.is_active = False
    user.name = "탈퇴한 사용자"
    user.nickname = "탈퇴한 사용자"
    user.phone = f"deleted:{user.id}"
    user.fcm_token = None

    photo_urls = [
        p.s3_url
        for p in db.query(UserPhoto).filter(UserPhoto.user_id == user.id).all()
    ]
    db.query(UserPhoto).filter(UserPhoto.user_id == user.id).delete()

    # 탈퇴한 상대에게는 답이 올 수 없다. 방을 닫지 않으면 남은 쪽이 계속
    # 말을 걸게 된다(채팅방 나가기는 같은 상황에서 이미 방을 닫는다).
    room_ids = [
        r.id
        for r in db.query(ChatRoom)
        .join(Match, ChatRoom.match_id == Match.id)
        .filter(or_(Match.user1_id == user.id, Match.user2_id == user.id))
        .all()
    ]
    if room_ids:
        db.query(ChatRoom).filter(ChatRoom.id.in_(room_ids)).update(
            {"is_active": False}, synchronize_session=False
        )

    db.commit()

    # 커밋 뒤에 부른다 — S3 실패가 탈퇴 자체를 롤백시키면 안 된다.
    delete_photo_objects(photo_urls)


def update_settings(db: Session, user: User, data: UpdateSettingsRequest) -> User:
    # None은 "변경 안 함". 처리방침 제1조 3항이 "동의는 언제든지 철회할 수
    # 있습니다"라고 하는데 철회 경로가 없었다.
    if data.chat_push_enabled is not None:
        user.chat_push_enabled = data.chat_push_enabled
    if data.marketing_consent is not None:
        user.marketing_consent = data.marketing_consent
    db.commit()
    db.refresh(user)
    return user
