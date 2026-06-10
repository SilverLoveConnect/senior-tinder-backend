from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 데이터베이스
    DATABASE_URL: str = ""

    # JWT 인증
    SECRET_KEY: str = ""
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

    # Firebase (실제 연동 시 필수로 변경)
    FIREBASE_CREDENTIALS_PATH: str = ""

    # Sentry (선택)
    SENTRY_DSN: str = ""

    # Supabase (실제 연동 시 필수로 변경)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    AI_API_URL: str = ""
    # 포트원 V1
    PORTONE_IMP_KEY: str = ""
    PORTONE_IMP_SECRET: str = ""

    # Supabase
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
