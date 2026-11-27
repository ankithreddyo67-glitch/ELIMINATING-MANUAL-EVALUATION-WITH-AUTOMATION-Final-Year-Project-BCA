"""Authentication, password hashing, and HMAC-SHA256 session token management."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from backend.config import SECRET_KEY, TOKEN_TTL_SECONDS

try:
    import bcrypt  # type: ignore
except ImportError:  # pragma: no cover - fallback when bcrypt isn't installed
    bcrypt = None


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt when available, else PBKDF2-SHA256."""
    if not password:
        raise ValueError("Password cannot be empty")
    if bcrypt is not None:
        salt = bcrypt.gensalt(rounds=10)
        digest = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        return f"bcrypt${digest}"

    salt_bytes = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 120_000)
    return (
        "pbkdf2$"
        + base64.b64encode(salt_bytes).decode("ascii")
        + "$"
        + base64.b64encode(dk).decode("ascii")
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt or PBKDF2 hash."""
    if not password or not stored_hash:
        return False

    if stored_hash.startswith("bcrypt$") and bcrypt is not None:
        raw_hash = stored_hash[len("bcrypt$"):].encode("utf-8")
        try:
            return bool(bcrypt.checkpw(password.encode("utf-8"), raw_hash))
        except ValueError:
            return False

    if stored_hash.startswith("pbkdf2$"):
        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False
        try:
            salt_bytes = base64.b64decode(parts[1])
            expected_dk = base64.b64decode(parts[2])
        except Exception:
            return False
        actual_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 120_000)
        return hmac.compare_digest(actual_dk, expected_dk)

    # Legacy plain bcrypt string support
    if stored_hash.startswith("$2") and bcrypt is not None:
        try:
            return bool(bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")))
        except ValueError:
            return False

    return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def create_token(user_payload: dict[str, Any], ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    """Create a signed HMAC-SHA256 bearer token."""
    now = int(time.time())
    payload = {
        "uid": user_payload["id"],
        "email": user_payload["email"],
        "name": user_payload["full_name"],
        "role": user_payload["role"],
        "iat": now,
        "exp": now + ttl_seconds,
    }
    header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


def verify_token(token: str) -> dict[str, Any] | None:
    """Validate signature and expiry of a bearer token and return its claims."""
    if not token or token.count(".") != 2:
        return None
    header_b64, payload_b64, sig_b64 = token.split(".")
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        claims = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return None

    if int(claims.get("exp", 0)) < int(time.time()):
        return None
    return claims
