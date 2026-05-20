# SQLAlchemy 엔진 및 세션 설정
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 연결 유효성 사전 확인
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """DB 세션 제너레이터 — 요청 종료 시 자동 close"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
