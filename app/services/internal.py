import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import PhotoReviewStatusEnum, User, UserPhoto
from app.models.manner import MannerFactorEnum
from app.schemas.internal import AIPhotoResultRequest
from app.services.fcm import notify_photo_approved
from app.services.manner import update_trust_score


def process_ai_photo_result(db: Session, data: AIPhotoResultRequest) -> dict:
    """AI 이미지 분석 결과 처리"""
    if data.analysis_status == "error":
        return {"message": "분석 실패", "photo_approved": False}

    photo = db.query(UserPhoto).filter(UserPhoto.s3_url == data.s3_url).first()
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")

    # 모델이 아직 미학습이라 자동 승인/거부 대신 사람 검수가 필요하다고
    # 표시된 사진은 자동 승인하지 않고 검수 대기 상태로 둔다.
    if data.needs_manual_review:
        photo.is_approved = False
        photo.review_status = PhotoReviewStatusEnum.pending
        db.commit()
        return {"message": "관리자 검수 대기", "photo_approved": False}

    if data.is_inappropriate:
        photo.is_approved = False
        photo.review_status = PhotoReviewStatusEnum.rejected
        db.commit()
        return {"message": "부적절한 사진", "photo_approved": False}

    if not data.has_face:
        photo.is_approved = False
        photo.review_status = PhotoReviewStatusEnum.rejected
        db.commit()
        return {"message": "얼굴 인식 실패", "photo_approved": False}

    # 여기까지 왔으면 has_face는 항상 True다 (위에서 not has_face는 return).
    photo.is_approved = True
    photo.review_status = PhotoReviewStatusEnum.approved
    update_trust_score(
        db=db,
        user=photo.user,
        factor=MannerFactorEnum.image_analysis,
        delta=15,
        reason="프로필 사진 등록 및 얼굴 인식 완료",
    )

    db.commit()

    if photo.is_approved and photo.user.fcm_token:
        notify_photo_approved(token=photo.user.fcm_token)

    return {"message": "처리 완료", "photo_approved": photo.is_approved}


def get_pending_photos(db: Session) -> dict:
    """관리자 검수가 필요한(review_status=pending) 사진 목록"""
    photos = (
        db.query(UserPhoto)
        .filter(UserPhoto.review_status == PhotoReviewStatusEnum.pending)
        .order_by(UserPhoto.created_at.asc())
        .all()
    )
    return {"photos": photos}


def review_photo(db: Session, photo_id: uuid.UUID, approve: bool) -> dict:
    """
    검수 대기 사진에 대한 관리자 최종 판정.

    pending 상태인 사진만 처리한다. 이 제약이 신뢰점수 중복 적용을 막는
    실질적 가드다 — update_trust_score()는 멱등하지 않아서(호출할 때마다
    MannerHistory 추가 + delta 누적) 같은 사진을 두 번 승인하면 +15가
    두 번 붙는다. 자동 승인 경로(process_ai_photo_result)는 pending을
    거치지 않고 바로 approved로 가므로 여기서 다시 잡히지 않는다.
    """
    photo = db.query(UserPhoto).filter(UserPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사진을 찾을 수 없습니다."
        )

    if photo.review_status != PhotoReviewStatusEnum.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"검수 대기 상태가 아닙니다. (현재: {photo.review_status.value})",
        )

    if not approve:
        photo.is_approved = False
        photo.review_status = PhotoReviewStatusEnum.rejected
        db.commit()
        return {"message": "검수 거부 처리 완료", "photo_approved": False}

    photo.is_approved = True
    photo.review_status = PhotoReviewStatusEnum.approved
    # 자동 승인 경로(has_face)와 동일한 가점을 딱 한 번 부여한다.
    update_trust_score(
        db=db,
        user=photo.user,
        factor=MannerFactorEnum.image_analysis,
        delta=15,
        reason="관리자 검수를 통해 프로필 사진 승인",
    )
    db.commit()

    if photo.user.fcm_token:
        notify_photo_approved(token=photo.user.fcm_token)

    return {"message": "검수 승인 처리 완료", "photo_approved": True}


def set_user_ban(db: Session, user_id: uuid.UUID, banned: bool) -> dict:
    """계정 정지/해제 (관리자용).

    신고 3회 누적이면 create_report가 is_banned=True로 만드는데, 이를 되돌리는
    경로가 어디에도 없어서 오신고 한 번이면 복구가 불가능했다. 이의 제기·오신고
    대응을 위해 해제 수단이 반드시 있어야 한다.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다."
        )

    user.is_banned = banned
    db.commit()

    return {
        "user_id": user.id,
        "is_banned": user.is_banned,
        "message": "계정을 정지했습니다." if banned else "계정 정지를 해제했습니다.",
    }
