"""S3 원본 파일 삭제.

DB의 UserPhoto 행만 지우고 S3 객체를 남기면, 버킷이 퍼블릭 리드인 이상
URL을 아는 사람은 탈퇴 후에도 얼굴 사진을 계속 볼 수 있다. 처리방침 제4조는
"저장소에 남은 원본 파일은 30일 이내 파기", 계정 삭제 안내는 "프로필 사진:
삭제"라고 적고 있어 문서와 코드가 어긋난 상태였다.
"""

import logging
from urllib.parse import unquote, urlparse

import boto3

from app.core.config import settings

logger = logging.getLogger(__name__)


def _client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def delete_photo_objects(s3_urls: list[str]) -> None:
    """S3 원본을 지운다.

    실패해도 예외를 올리지 않는다 — 탈퇴·사진삭제라는 사용자의 권리 행사가
    S3 장애로 막히면 안 된다. 대신 로그를 남겨 수동 파기 대상으로 남긴다
    (처리방침이 "30일 이내"라 재시도 여유가 있다).
    """
    keys = [
        {"Key": unquote(urlparse(url).path).lstrip("/")} for url in s3_urls if url
    ]
    if not keys:
        return

    try:
        _client().delete_objects(
            Bucket=settings.AWS_S3_BUCKET, Delete={"Objects": keys}
        )
    except Exception:
        logger.exception("S3 원본 삭제 실패 — 수동 파기 대상: %s", keys)
