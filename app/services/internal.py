from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import UserPhoto
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

    # ⚠️ 임시(베타): 부적절 필터 미학습 상태라 승인 판정 제외. 로그만 수집.
    # 학습된 모델 배포 후 반드시 복원할 것 — 복원 전 일반 공개(런칭) 금지!
    print(
        f"[ai-photo] user={data.user_id} inappropriate={data.is_inappropriate}"
        f"({data.inappropriate_score:.3f})"
    )

    if not data.has_face:
        photo.is_approved = False
        db.commit()
        return {"message": "얼굴 인식 실패", "photo_approved": False}

    if data.has_face:
        photo.is_approved = True
        update_trust_score(
            db=db,
            user=photo.user,
            factor=MannerFactorEnum.image_analysis,
            delta=15,
            reason="프로필 사진 등록 및 얼굴 인식 완료",
        )
    else:
        update_trust_score(
            db=db,
            user=photo.user,
            factor=MannerFactorEnum.image_analysis,
            delta=5,
            reason="프로필 사진 업로드 완료",
        )

    db.commit()

    if photo.is_approved and photo.user.fcm_token:
        notify_photo_approved(token=photo.user.fcm_token)

    return {"message": "처리 완료", "photo_approved": photo.is_approved}
