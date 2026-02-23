"""Service for resolving system settings with DB-first, env-fallback strategy."""
import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.config import settings
from app.models.system_settings import SystemSettings
from app.services.encryption import decrypt_value

logger = logging.getLogger(__name__)


def get_llm_api_key(provider: Literal["openai", "anthropic"], db: Session) -> str:
    """
    Resolve an LLM API key: check database first, fall back to .env.

    Raises ValueError if no key is found anywhere.
    """
    row = db.query(SystemSettings).first()

    if row:
        if provider == "openai" and row.openai_api_key_encrypted:
            decrypted = decrypt_value(row.openai_api_key_encrypted)
            if decrypted:
                return decrypted
        elif provider == "anthropic" and row.anthropic_api_key_encrypted:
            decrypted = decrypt_value(row.anthropic_api_key_encrypted)
            if decrypted:
                return decrypted

    # Fallback to environment
    env_key = settings.openai_api_key if provider == "openai" else settings.anthropic_api_key
    if env_key:
        return env_key

    raise ValueError(
        f"No API key configured for provider '{provider}'. "
        "Set it via the admin settings page or the environment variable."
    )
