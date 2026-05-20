# 공통 FastAPI 의존성 (get_db, get_current_user)
from collections.abc import Generator
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal

bearer_scheme = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """DB 세션 의존성 — database.py의 get_db와 동일, Depends 전용"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Any:
    """JWT 토큰 검증 후 현재 유저 반환 (stub — 유저 모델 추가 후 구현)"""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject: str | None = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에서 사용자 정보를 찾을 수 없습니다.",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        )
    # TODO: User 모델 추가 후 db.get(User, subject) 로 교체
    return {"id": subject}
