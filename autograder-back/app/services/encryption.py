"""Symmetric encryption for sensitive settings stored in the database."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _derive_key() -> bytes:
    """Derive a Fernet-compatible key from jwt_secret_key via SHA-256."""
    digest = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64-encoded ciphertext."""
    if not plaintext:
        return ""
    f = Fernet(_derive_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Returns the original plaintext."""
    if not ciphertext:
        return ""
    f = Fernet(_derive_key())
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return ""
