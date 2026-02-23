"""Tests for app.services.encryption module."""
import pytest
from unittest.mock import patch


@patch("app.services.encryption.settings")
def test_encrypt_decrypt_roundtrip(mock_settings):
    mock_settings.jwt_secret_key = "test-secret-key-for-encryption"
    from app.services.encryption import encrypt_value, decrypt_value

    original = "sk-proj-abc123456789"
    encrypted = encrypt_value(original)
    assert encrypted != original
    assert encrypted != ""
    decrypted = decrypt_value(encrypted)
    assert decrypted == original


@patch("app.services.encryption.settings")
def test_encrypt_empty_string(mock_settings):
    mock_settings.jwt_secret_key = "test-secret-key-for-encryption"
    from app.services.encryption import encrypt_value

    assert encrypt_value("") == ""


@patch("app.services.encryption.settings")
def test_decrypt_empty_string(mock_settings):
    mock_settings.jwt_secret_key = "test-secret-key-for-encryption"
    from app.services.encryption import decrypt_value

    assert decrypt_value("") == ""


@patch("app.services.encryption.settings")
def test_decrypt_invalid_ciphertext(mock_settings):
    mock_settings.jwt_secret_key = "test-secret-key-for-encryption"
    from app.services.encryption import decrypt_value

    result = decrypt_value("not-a-valid-ciphertext")
    assert result == ""


@patch("app.services.encryption.settings")
def test_decrypt_with_wrong_key(mock_settings):
    mock_settings.jwt_secret_key = "key-one"
    from app.services.encryption import encrypt_value, decrypt_value

    encrypted = encrypt_value("my-secret-token")

    mock_settings.jwt_secret_key = "key-two"
    result = decrypt_value(encrypted)
    assert result == ""
