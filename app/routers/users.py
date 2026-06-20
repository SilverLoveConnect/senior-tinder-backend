import os
import uuid as uuid_lib

import boto3
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User, UserPhoto
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


@router.post("/me/photos")
def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """프로필 사진 업로드 — S3 저장 후 AI 서버에 분석 요청"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    # S3 업로드
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    key = f"photos/{current_user.id}/{uuid_lib.uuid4()}{ext}"
    s3.upload_fileobj(
        file.file,
        settings.AWS_S3_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type},
    )
    s3_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    # DB 저장 (is_approved=False — AI 분석 완료 전)
    photo = UserPhoto(user_id=current_user.id, s3_url=s3_url, is_approved=False)
    db.add(photo)
    db.commit()

    # AI 서버에 분석 요청 (실패해도 업로드는 성공 처리)
    try:
        httpx.post(
            f"{settings.AI_API_URL}/api/v1/image/analyze/url",
            json={"s3_url": s3_url, "user_id": str(current_user.id)},
            timeout=3,
        )
    except Exception:
        pass

    return {"s3_url": s3_url, "status": "analyzing"}


@router.delete("/me/photos")
def delete_photo(
    s3_url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """프로필 사진 삭제"""
    photo = db.query(UserPhoto).filter(
        UserPhoto.s3_url == s3_url,
        UserPhoto.user_id == current_user.id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")
    db.delete(photo)
    db.commit()
    return {"message": "삭제 완료"}
