"""
Cryptographic and security utilities: password hashing, session tokens, and sanitization.
"""
import bcrypt
import hmac
import secrets
import hashlib
from typing import Optional


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash or legacy plaintext."""
    if not hashed_password:
        return False
    # Backward compatibility with legacy plaintext passwords (e.g. '12345678')
    if not hashed_password.startswith("$2b$") and not hashed_password.startswith("$2a$"):
        return hmac.compare_digest(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def generate_session_token() -> str:
    """Generate a high-entropy URL-safe session token."""
    return secrets.token_urlsafe(32)


def sha256_hash(data: str) -> str:
    """Generate SHA256 digest of input string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
