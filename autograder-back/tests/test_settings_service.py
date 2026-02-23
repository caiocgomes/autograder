"""Tests for app.services.settings module."""
import pytest
from unittest.mock import patch, MagicMock, Mock
from app.services.settings import get_llm_api_key
from app.models.system_settings import SystemSettings


def test_get_key_from_database():
    db = MagicMock()
    row = Mock(spec=SystemSettings)
    row.anthropic_api_key_encrypted = "encrypted-value"
    row.openai_api_key_encrypted = None
    db.query.return_value.first.return_value = row

    with patch("app.services.settings.decrypt_value", return_value="sk-ant-real-key"):
        result = get_llm_api_key("anthropic", db)

    assert result == "sk-ant-real-key"


def test_get_key_fallback_to_env_when_db_empty():
    db = MagicMock()
    db.query.return_value.first.return_value = None

    with patch("app.services.settings.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-env-openai-key"
        result = get_llm_api_key("openai", db)

    assert result == "sk-env-openai-key"


def test_get_key_fallback_to_env_when_db_field_empty():
    db = MagicMock()
    row = Mock(spec=SystemSettings)
    row.openai_api_key_encrypted = ""
    db.query.return_value.first.return_value = row

    with patch("app.services.settings.decrypt_value", return_value=""), \
         patch("app.services.settings.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-env-fallback"
        result = get_llm_api_key("openai", db)

    assert result == "sk-env-fallback"


def test_get_key_db_takes_precedence_over_env():
    db = MagicMock()
    row = Mock(spec=SystemSettings)
    row.openai_api_key_encrypted = "encrypted"
    db.query.return_value.first.return_value = row

    with patch("app.services.settings.decrypt_value", return_value="sk-from-db"), \
         patch("app.services.settings.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-from-env"
        result = get_llm_api_key("openai", db)

    assert result == "sk-from-db"


def test_get_key_raises_when_no_key_anywhere():
    db = MagicMock()
    db.query.return_value.first.return_value = None

    with patch("app.services.settings.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        with pytest.raises(ValueError, match="No API key configured"):
            get_llm_api_key("anthropic", db)
