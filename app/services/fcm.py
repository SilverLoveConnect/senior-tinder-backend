# Firebase FCM 푸시 알림 발송 서비스
import logging

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

logger = logging.getLogger(__name__)

if not firebase_admin._apps:
    if settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
    else:
        logger.warning("FIREBASE_CREDENTIALS_PATH가 설정되지 않아 FCM 초기화를 스킵합니다.")


def send_push_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    """단일 기기에 푸시 알림 발송"""
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )
        messaging.send(message)
        return True
    except Exception:
        logger.exception("FCM 푸시 알림 발송 실패")
        return False


def notify_new_match(token: str, matched_user_nickname: str) -> bool:
    """새로운 매칭 알림"""
    return send_push_notification(
        token=token,
        title="새로운 매칭! 💕",
        body=f"{matched_user_nickname}님과 매칭됐어요",
        data={"type": "match"},
    )


def notify_new_message(token: str, sender_nickname: str, message: str) -> bool:
    """새로운 메시지 알림"""
    return send_push_notification(
        token=token,
        title=f"{sender_nickname}님의 메시지",
        body=message[:50],
        data={"type": "message"},
    )


def notify_photo_approved(token: str) -> bool:
    """프로필 사진 승인 알림"""
    return send_push_notification(
        token=token,
        title="프로필 사진 승인",
        body="사진이 승인됐어요. 매칭을 시작해보세요!",
        data={"type": "photo_approved"},
    )
