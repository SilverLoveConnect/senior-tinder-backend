from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 데이터베이스 (필수 — 비어있으면 기동 실패)
    DATABASE_URL: str = Field(min_length=1)

    # JWT 인증 (SECRET_KEY 필수 — 비어있으면 기동 실패)
    SECRET_KEY: str = Field(min_length=1)
    ALGORITHM: str = "HS256"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AWS S3 (실제 연동 시 필수로 변경)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "ap-northeast-2"

    # Solapi SMS (실제 연동 시 필수로 변경)
    SOLAPI_API_KEY: str = ""
    SOLAPI_API_SECRET: str = ""
    SOLAPI_SENDER: str = ""

    # Google Cloud Vision (실제 연동 시 필수로 변경)
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Firebase — 로컬 개발: 서비스 계정 JSON 파일 경로
    FIREBASE_CREDENTIALS_PATH: str = ""
    # Firebase — 프로덕션(Railway 등 파일 업로드가 마땅찮은 환경): 서비스 계정
    # JSON 전체를 Base64로 인코딩한 값. 설정돼 있으면 PATH보다 우선한다.
    FIREBASE_CREDENTIALS_JSON: str = ""

    # Sentry (선택)
    SENTRY_DSN: str = ""

    # Supabase (실제 연동 시 필수로 변경)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    AI_API_URL: str = ""
    AI_IMAGE_API_URL: str = ""
    # 포트원 V1
    PORTONE_IMP_KEY: str = ""
    PORTONE_IMP_SECRET: str = ""

    # Supabase
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # 내부 서비스(AI 서버 등) 콜백 인증 토큰
    INTERNAL_TOKEN: str = ""

    # 스토어 심사관 검수용 고정 인증코드 (두 값 모두 설정된 경우에만 활성화)
    REVIEW_TEST_PHONE: str = ""
    REVIEW_TEST_CODE: str = ""

    # CORS 허용 도메인 (콤마 구분, 프로덕션 배포 환경변수로 설정)
    # 비어있으면 전체 허용(로컬 개발 기본값) — 프로덕션에서는 반드시 설정할 것
    CORS_ALLOWED_ORIGINS: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ALLOWED_ORIGINS가 비어있으면 전체 허용(로컬 개발 기본값)"""
        if not self.CORS_ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
