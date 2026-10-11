"""Encryption for API keys entered in the app (Fernet). Keys are never logged or returned to clients."""
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings

SECRET_FILE = Path(__file__).resolve().parents[2] / ".strongprep-secret"  # demo only; gitignored


class SecretsUnavailable(Exception):
    pass


def _fernet(settings: Settings) -> Fernet:
    key = settings.app_secret_key
    if not key:
        if not settings.is_demo:
            raise SecretsUnavailable("APP_SECRET_KEY is required in live mode to store API keys.")
        if SECRET_FILE.exists():
            key = SECRET_FILE.read_text().strip()
        else:
            key = Fernet.generate_key().decode()
            SECRET_FILE.write_text(key)
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise SecretsUnavailable("APP_SECRET_KEY is not a valid Fernet key.") from exc


def encrypt(settings: Settings, plaintext: str) -> str:
    return _fernet(settings).encrypt(plaintext.encode()).decode()


def decrypt(settings: Settings, token: str) -> str:
    try:
        return _fernet(settings).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretsUnavailable("The stored API key cannot be decrypted. Enter it again.") from exc
