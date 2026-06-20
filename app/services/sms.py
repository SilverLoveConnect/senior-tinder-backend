from solapi import SolapiMessageService
from solapi.model import RequestMessage

from app.core.config import settings


def send_verification_sms(phone: str, code: str) -> None:
    """SMS 인증번호 발송"""
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
