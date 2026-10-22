from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    # Deprecated v1.2 master switch: /api/rewrite and friends were removed in
    # v1.3, but the setting is kept so stray env values fail validation loudly
    # instead of being silently ignored.
    REWRITE_ENABLED: bool = False
    CONTRIBUTIONS_ENABLED: bool = False
    ADMIN_API_ENABLED: bool = False
    GROQ_API_KEY: str | None = None
    GROQ_REWRITE_MODELS: str | None = None
    ADMIN_API_KEY: str | None = None
    DATABASE_URL: str = "sqlite:///./dev.db"
    TRUSTED_PROXY_HOSTS: str = "127.0.0.1,localhost,::1"
    TRUST_PRIVATE_PROXIES: bool = False
    # ------- v1.3 Humanize (mô hình chuyên biệt, tương thích OpenAI) -------
    # Base URL OpenAI-compatible của humanizer endpoint, ví dụ
    # "https://host:8000/v1" (vLLM — xem training/serve/runpod_vllm.md).
    HUMANIZER_API_BASE: str | None = None
    # API key của endpoint humanizer (vLLM --api-key). Trống nếu endpoint
    # không đặt mật khẩu.
    HUMANIZER_API_KEY: str | None = None
    # Trùng với --served-model-name của vLLM (mặc định "humanizer-vi").
    HUMANIZER_MODEL: str = "humanizer-vi"
    # Timeout cho một lượt gọi humanizer (T4 ~<20s/400 từ, để dư an toàn).
    HUMANIZER_TIMEOUT_SECONDS: float = 45.0
    # Khi mô hình chuyên biệt chưa được phục vụ, dùng pipeline Groq hiện có
    # để web vẫn hoạt động (provider "groq-fallback").
    HUMANIZER_FALLBACK_GROQ: bool = True
    # Bật để trả về chi tiết lỗi gọi Groq trong response (HTTP status,
    # raw message, danh sách model đã thử). Chỉ nên bật trong dev.
    DEBUG_ERRORS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
