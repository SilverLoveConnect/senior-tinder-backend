# Firebase FCM 푸시 알림 발송 서비스
import base64
import json
import logging

import firebase_admin
import httpx
from firebase_admin import credentials, messaging

from app.core.config import settings

logger = logging.getLogger(__name__)

if not firebase_admin._apps:
    if settings.FIREBASE_CREDENTIALS_JSON:
        # Railway 등 파일 업로드가 마땅찮은 환경 — Base64로 인코딩된 서비스
        # 계정 JSON을 디코드해서 dict로 바로 넘긴다(파일 필요 없음).
        try:
            cred_info = json.loads(base64.b64decode(settings.FIREBASE_CREDENTIALS_JSON))
            cred = credentials.Certificate(cred_info)
            firebase_admin.initialize_app(cred)
        except Exception:
            logger.exception("FIREBASE_CREDENTIALS_JSON 파싱 실패 — FCM 초기화 스킵")
    elif settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
    else:
        logger.warning(
            "FIREBASE_CREDENTIALS_JSON/FIREBASE_CREDENTIALS_PATH가 설정되지 않아 FCM 초기화를 스킵합니다."
        )


EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _is_expo_token(token: str) -> bool:
    return token.startswith(("ExponentPushToken[", "ExpoPushToken["))


def _send_expo(token: str, title: str, body: str, data: dict | None) -> bool:
    """Expo Push API로 발송 — Expo가 iOS(APNs)·Android(FCM)로 전달한다."""
    try:
        res = httpx.post(
            EXPO_PUSH_URL,
            json={"to": token, "title": title, "body": body, "data": data or {},
                  "sound": "default", "channelId": "default", "priority": "high"},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        ticket = res.json().get("data")
        if isinstance(ticket, list):
            ticket = ticket[0] if ticket else {}
        if res.status_code == 200 and (ticket or {}).get("status") == "ok":
            return True
        logger.warning("Expo 푸시 발송 실패: http=%s ticket=%s", res.status_code, ticket)
        return False
    except Exception:
        logger.exception("Expo 푸시 발송 실패")
        return False


def send_push_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    """단일 기기에 푸시 알림 발송.

    앱은 Expo 푸시 토큰을 등록한다. 이전 앱은 네이티브 토큰(iOS에서는 APNs 토큰)을
    등록했고 여기서 Firebase로 보냈는데, Firebase는 APNs 토큰을 받지 않아 iOS 알림이
    한 번도 도착하지 않았다. 구버전 앱이 남긴 토큰은 기존 Firebase 경로로 둔다.
    """
    if _is_expo_token(token):
        return _send_expo(token, title, body, data)
    if not firebase_admin._apps:
        logger.warning("Firebase 미초기화 — 비 Expo 토큰 푸시 스킵")
        return False
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


def notify_new_message(
    token: str, sender_nickname: str, message: str, room_id: str
) -> bool:
    """새로운 메시지 알림"""
    return send_push_notification(
        token=token,
        title=f"{sender_nickname}님의 메시지",
        body=message[:50],
        data={"type": "message", "room_id": room_id},
    )


def notify_photo_approved(token: str) -> bool:
    """프로필 사진 승인 알림"""
    return send_push_notification(
        token=token,
        title="프로필 사진 승인",
        body="사진이 승인됐어요. 매칭을 시작해보세요!",
        data={"type": "photo_approved"},
    )
