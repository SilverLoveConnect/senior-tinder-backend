from solapi import SolapiMessageService
from solapi.model import RequestMessage

from app.core.config import settings


def send_verification_sms(phone: str, code: str) -> None:
    """SMS 인증번호 발송"""
    if not settings.SOLAPI_API_KEY:
        print(f"[SMS-BYPASS] {phone} → {code}")
        return

    try:
        service = SolapiMessageService(
            api_key=settings.SOLAPI_API_KEY,
            api_secret=settings.SOLAPI_API_SECRET,
        )
        message = RequestMessage(
            to=phone,
            from_=settings.SOLAPI_SENDER,
            text=f"[시나브로] 인증번호: {code}",
        )
        service.send(message)
    except Exception as e:
        # 발송 실패해도 인증 흐름은 계속 진행
        # 서버 로그에서 코드 확인 가능
        print(f"[SMS-FAIL] {phone} → {code} | error: {e}")
