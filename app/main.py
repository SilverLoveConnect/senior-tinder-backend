# FastAPI 앱 진입점
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, block, matching, point, report, users

# Sentry 초기화 (DSN이 설정된 경우에만)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
    )

app = FastAPI(
    title="Senior Tinder API",
    version="0.1.0",
)

# CORS 미들웨어 — 개발환경 전체 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(matching.router)
app.include_router(report.router)
app.include_router(block.router)
app.include_router(point.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """서버 상태 확인 엔드포인트"""
    return {"status": "ok"}
