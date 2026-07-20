import logging

from solapi import SolapiMessageService
from solapi.model import RequestMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_verification_sms(phone: str, code: str) -> None:
    """SMS 인증번호 발송"""
    if not settings.SOLAPI_API_KEY:
        logger.warning("SOLAPI_API_KEY가 설정되지 않아 SMS 발송을 스킵합니다.")
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
    except Exception:
        # 발송 실패해도 인증 흐름은 계속 진행
        logger.exception("SMS 발송 실패")
