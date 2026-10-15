"""
Konfigurasi terpusat menggunakan Pydantic Settings.
Semua service membaca konfigurasi dari sini — tidak membaca os.environ langsung.
"""
from __future__ import annotations

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "ai-chatbot-mvp"
    app_secret_key: SecretStr
    frontend_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"

    # ── Database ────────────────────────────────────────────────────────────
    database_url: SecretStr
    postgres_db: str = "ai_chatbot"
    postgres_user: str = "ai_chatbot_app"
    postgres_password: SecretStr

    # ── Authentication ──────────────────────────────────────────────────────
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ── LLM ────────────────────────────────────────────────────────────────
    llm_provider: str = "openai"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    local_llm_base_url: str | None = None
    local_llm_model: str | None = None

    # ── Embedding ──────────────────────────────────────────────────────────
    embedding_provider: str = "openai"  # openai | ollama
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ── OCR & Ingestion ────────────────────────────────────────────────────
    ocr_provider: str = "paddleocr"
    max_upload_size_mb: int = 25
    allowed_upload_extensions: str = "pdf,png,jpg,jpeg"
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 5

    # ── n8n ───────────────────────────────────────────────────────────────
    n8n_api_base_url: str = "http://n8n:5678"
    n8n_webhook_base_url: str = "http://n8n:5678"

    # ── Storage ────────────────────────────────────────────────────────────
    storage_backend: str = "local"
    upload_dir: str = "/app/data/uploads"
    encryption_key: SecretStr | None = None
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key: SecretStr | None = None
    s3_secret_key: SecretStr | None = None

    # ── Observability ──────────────────────────────────────────────────────
    log_level: str = "INFO"
    otel_service_name: str = "ai-chatbot-api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Validators ─────────────────────────────────────────────────────────

    @field_validator("embedding_dimension")
    @classmethod
    def positive_dimension(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("embedding_dimension harus lebih dari nol")
        return v

    @field_validator("max_upload_size_mb", "retrieval_top_k", "chunk_size", "chunk_overlap")
    @classmethod
    def positive_limits(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Nilai batas tidak boleh negatif")
        return v

    @field_validator("app_env")
    @classmethod
    def valid_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"app_env harus salah satu dari: {allowed}")
        return v

    @model_validator(mode="after")
    def check_llm_credentials(self) -> "Settings":
        if self.llm_provider == "openai" and not self.openai_api_key:
            # Warning — tidak raise agar development tanpa key tetap bisa jalan
            import warnings
            warnings.warn(
                "llm_provider=openai tapi OPENAI_API_KEY belum diset. "
                "Endpoint chat akan gagal.",
                stacklevel=2,
            )
        if self.llm_provider == "local" and not self.local_llm_base_url:
            raise ValueError(
                "llm_provider=local membutuhkan LOCAL_LLM_BASE_URL"
            )
        return self

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_upload_extensions.split(",")}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


# Singleton — import ini di seluruh aplikasi
settings = Settings()  # type: ignore[call-arg]
