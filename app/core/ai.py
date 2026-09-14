from app.core.config import settings


def ai_headers() -> dict[str, str]:
    """AI 서버 호출 헤더.

    AI 서버는 AI_API_KEY가 설정되면 X-API-Key가 없는 요청을 401로 막는다. 백엔드가
    헤더를 안 보내면 키를 켜는 순간 스캠 탐지·사진 검수·자기소개 추천이 전부 멈춘다.
    키가 비어 있으면 헤더를 붙이지 않아 지금(키 미설정) 동작은 그대로다.
    """
    return {"X-API-Key": settings.AI_API_KEY} if settings.AI_API_KEY else {}
