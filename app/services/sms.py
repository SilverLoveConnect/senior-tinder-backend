from solapi import SolapiMessageService
from solapi.model import RequestMessage
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_verification_sms(phone: str, code: str) -> None:

    # TODO: SOLAPI IP 허용 후 활성화
    logger.info(f"[SMS] {phone} → 인증번호: {code}")
    print(f"[SMS] {phone} → 인증번호: {code}")
    return

    # 아래 코드는 IP 허용 후 활성화
    from solapi import SolapiMessageService
    from solapi.model import RequestMessage

    service = SolapiMessageService(
        api_key=settings.SOLAPI_API_KEY,
        api_secret=settings.SOLAPI_API_SECRET,
    )
    message = RequestMessage(
        to=phone,
        from_=settings.SOLAPI_SENDER,
        text=f"[사랑은죽을때까지] 인증번호: {code}",
    )
    service.send(message)
