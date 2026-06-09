from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import UserPhoto
from app.models.manner import MannerFactorEnum
from app.schemas.internal import AIPhotoResultRequest
from app.services.manner import update_manner_score


def process_ai_photo_result(db: Session, data: AIPhotoResultRequest) -> dict:
    """AI 이미지 분석 결과 처리"""
    if data.analysis_status == "failed":
        return {"message": "분석 실패", "photo_approved": False}
    photo = db.query(UserPhoto).filter(UserPhoto.s3_url == data.s3_url).first()
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")

    if data.is_inappropriate:
        photo.is_approved = False
        db.commit()
        return {"message": "부적절한 사진", "photo_approved": False}

    if not data.has_face:
        photo.is_approved = False
        db.commit()
        return {"message": "얼굴이 감지되지 않았습니다.", "photo_approved": False}

    if data.quality_score >= 0.6:
        photo.is_approved = True
        user = photo.user
        update_manner_score(
            db=db,
            user=user,
            factor=MannerFactorEnum.image_analysis,
            delta=5,
            reason="프로필 사진 품질 통과",
        )
    else:
        photo.is_approved = False

    db.commit()
    return {"message": "처리 완료", "photo_approved": photo.is_approved}
