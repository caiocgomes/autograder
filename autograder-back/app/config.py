from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://autograder:autograder@localhost:5432/autograder"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # JWT
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Security
    bcrypt_cost_factor: int = 12
    rate_limit_failed_logins: int = 5
    rate_limit_window_minutes: int = 15

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@autograder.com"

    # LLM API
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: Literal["openai", "anthropic"] = "openai"

    # Sandbox
    docker_image_sandbox: str = "autograder-sandbox:latest"
    sandbox_timeout_seconds: int = 30
    sandbox_memory_limit_mb: int = 512
    sandbox_cpu_limit: int = 1

    # File Uploads
    max_exercise_file_size_mb: int = 10
    max_submission_file_size_mb: int = 10
    upload_base_dir: Path = Path("./uploads")

    # CORS
    cors_origins: str = "*"  # Comma-separated origins or * for dev

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "text"

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    base_dir: Path = Path(__file__).parent.parent

    # Hotmart integration
    hotmart_hottok: str = ""
    hotmart_webhook_enabled: bool = False
    hotmart_client_id: str = ""
    hotmart_client_secret: str = ""
    hotmart_api_base: str = "https://developers.hotmart.com/payments/api/v1"
    hotmart_token_url: str = "https://api-sec-vlc.hotmart.com/security/oauth/token"

    # Discord integration
    discord_bot_token: str = ""
    discord_guild_id: str = ""
    discord_registration_channel_id: str = ""
    discord_enabled: bool = False

    # ManyChat integration
    manychat_api_token: str = ""
    manychat_enabled: bool = False
    manychat_onboarding_flow_id: str = ""
    manychat_welcome_flow_id: str = ""
    manychat_churn_flow_id: str = ""
    manychat_welcome_back_flow_id: str = ""
    manychat_new_assignment_flow_id: str = ""
    manychat_deadline_reminder_flow_id: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Global settings instance
settings = Settings()
