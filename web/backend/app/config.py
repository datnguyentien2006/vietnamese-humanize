from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    REWRITE_ENABLED: bool = False
    CONTRIBUTIONS_ENABLED: bool = False
    ADMIN_API_ENABLED: bool = False
    GROQ_API_KEY: str | None = None
    GROQ_REWRITE_MODELS: str | None = None
    ADMIN_API_KEY: str | None = None
    DATABASE_URL: str = "sqlite:///./dev.db"
    TRUSTED_PROXY_HOSTS: str = "127.0.0.1,localhost,::1"
    TRUST_PRIVATE_PROXIES: bool = False
    # Bật để trả về chi tiết lỗi gọi Groq trong response (HTTP status,
    # raw message, danh sách model đã thử). Chỉ nên bật trong dev.
    DEBUG_ERRORS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()