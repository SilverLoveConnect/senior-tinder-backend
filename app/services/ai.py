# AI 서버(senior-tinder-ai) 호출 공통 유틸
from app.core.config import settings


def ai_headers() -> dict[str, str]:
    """AI 서버 인증 헤더.

    AI 서버는 AI_API_KEY가 설정되면 /health를 제외한 모든 요청에 X-API-Key를
    요구한다. 호출부(스캠 감지·사진 분석)는 예외를 삼키도록 되어 있어서 키를
    빠뜨리면 401을 받고도 요청은 그대로 통과한다 — 즉 기능이 조용히 꺼진다.
    그래서 헤더는 여기서만 만든다.

    AI_API_KEY 미설정 시 빈 dict를 돌려주므로 무인증 AI 서버와도 그대로 붙는다.
    """
    if not settings.AI_API_KEY:
        return {}
    return {"X-API-Key": settings.AI_API_KEY}
