import io
import os
import uuid as uuid_lib

import boto3
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import PhotoReviewStatusEnum, User, UserPhoto
from app.schemas.users import (
    FcmTokenRequest,
    UpdateProfileRequest,
    UpdateSettingsRequest,
    UpdateSettingsResponse,
    UserProfileResponse,
)
from app.services import users as users_service
from app.services.s3 import delete_photo_objects

router = APIRouter(prefix="/users", tags=["users"])

# 업로드 제한 — 없으면 한 계정이 대용량 파일을 무제한으로 올려 S3 비용과
# Modal 분석 호출이 그대로 늘어난다.
MAX_PHOTOS_PER_USER = 6
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10MB

# 파일 앞부분 시그니처(매직 바이트). Content-Type은 클라이언트가 보낸 값이라
# 위조할 수 있어 단독으로는 신뢰할 수 없다.
_IMAGE_SIGNATURES = (
    b"\xff\xd8\xff",       # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
)


def _looks_like_image(head: bytes) -> bool:
    if any(head.startswith(sig) for sig in _IMAGE_SIGNATURES):
        return True
    # RIFF....WEBP / ....ftypheic·heix·mif1 (HEIC) — 컨테이너는 앞 12바이트로 판별
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return True
    if head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"mif1", b"msf1"):
        return True
    return False


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


@router.put("/me/settings", response_model=UpdateSettingsResponse)
def update_settings(
    body: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """알림 등 유저 설정 갱신 (현재는 채팅 푸시 알림 수신 여부)"""
    return users_service.update_settings(db, current_user, body)


@router.post("/me/fcm-token")
def update_fcm_token(
    body: FcmTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """푸시 알림용 FCM 토큰 등록/갱신"""
    # 같은 기기에서 A가 로그아웃하고 B가 로그인하면 두 계정이 같은 토큰을 갖는다.
    # 회수하지 않으면 A에게 오는 매칭·메시지 알림이 B의 기기로 발송된다 —
    # 알림 본문에 메시지 앞 50자가 실리므로 대화 내용이 제3자에게 노출된다.
    db.query(User).filter(
        User.fcm_token == body.fcm_token, User.id != current_user.id
    ).update({"fcm_token": None}, synchronize_session=False)
    current_user.fcm_token = body.fcm_token
    db.commit()
    return {"message": "저장 완료"}


@router.post("/me/photos")
def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """프로필 사진 업로드 — S3 저장 후 AI 서버에 분석 요청"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    # 거부된 사진은 한도에서 제외한다.
    # /users/me는 승인된 사진만 내려주므로(users.py: services) 사용자는 거부된
    # 사진을 화면에서 볼 수도, 지울 수도 없다. 그런데 한도를 전체 행으로 세면
    # 얼굴이 안 나온 사진을 6장 올린 사용자는 프로필 사진 0장인 채로 업로드가
    # 영구히 막힌다(실제로 심사용 계정이 그 상태가 됐다).
    photo_count = (
        db.query(UserPhoto)
        .filter(
            UserPhoto.user_id == current_user.id,
            UserPhoto.review_status != PhotoReviewStatusEnum.rejected,
        )
        .count()
    )
    if photo_count >= MAX_PHOTOS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"사진은 최대 {MAX_PHOTOS_PER_USER}장까지 등록할 수 있습니다.",
        )

    # 상한보다 1바이트 더 읽어서 초과 여부를 판단한다(초과분 전체를 메모리에 담지 않음).
    content = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"사진 용량은 {MAX_PHOTO_BYTES // (1024 * 1024)}MB를 넘을 수 없습니다.",
        )
    if not _looks_like_image(content[:12]):
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
        io.BytesIO(content),
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
            settings.AI_IMAGE_API_URL,
            json={"s3_url": s3_url, "user_id": str(current_user.id)},
            timeout=3,
        )
    except Exception:
        pass

    return {"s3_url": s3_url, "status": "analyzing"}


@router.delete("/me", status_code=204)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """회원 탈퇴 (소프트 삭제)"""
    users_service.delete_account(db, current_user)
    return None


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
    # DB 행만 지우면 S3 원본이 남아 URL을 아는 사람은 계속 볼 수 있다.
    delete_photo_objects([s3_url])
    return {"message": "삭제 완료"}
