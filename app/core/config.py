# 환경변수 설정 관리 (pydantic-settings 기반)
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 데이터베이스
    DATABASE_URL: str

    # JWT 인증
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AWS S3
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET: str
    AWS_REGION: str

    # Solapi SMS
    SOLAPI_API_KEY: str
    SOLAPI_API_SECRET: str
    SOLAPI_SENDER: str

    # Google Cloud Vision
    GOOGLE_APPLICATION_CREDENTIALS: str

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str

    # Sentry (선택)
    SENTRY_DSN: str = ""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
