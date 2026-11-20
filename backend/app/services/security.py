"""
Security, Authentication & Role-Based Access Control (RBAC) Module for HUCE Smart Kiosk.
Provides:
1. PBKDF2-HMAC-SHA256 PIN Hashing & Verification (260,000 iterations + 16-byte random salt).
2. Cryptographic JWT (HS256) Generation & Verification with Short-Lived TTL (300s).
3. In-Memory JTI Token Revocation Store with Automatic Expiration Cleanup.
4. FastAPI Security Dependencies:
   - get_current_user
   - get_optional_user
   - require_admin
   - assert_student_owner_or_admin
"""

import hashlib
import hmac
import os
import secrets
import time
import uuid
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Ephemeral secret fallback if HUCE_JWT_SECRET is not configured (at least 32 bytes for HMAC-SHA256)
_FALLBACK_JWT_SECRET = secrets.token_hex(32)

# Global in-memory revoked tokens store: {jti: exp_timestamp}
_revoked_tokens_store: Dict[str, int] = {}

http_bearer = HTTPBearer(auto_error=False)
security_scheme = http_bearer


def get_jwt_secret() -> str:
    """Returns the JWT secret from environment or falls back to an ephemeral secure key (>= 32 bytes)."""
    sec = os.environ.get("HUCE_JWT_SECRET", "").strip()
    if sec and len(sec.encode("utf-8")) >= 32:
        return sec
    return _FALLBACK_JWT_SECRET


def hash_pin(plain_pin: str) -> str:
    """
    Hashes a student or admin PIN using PBKDF2-HMAC-SHA256 with 260,000 iterations
    and a 16-byte cryptographically secure random salt.
    Format: <salt_hex>$<hash_hex>
    """
    if not plain_pin or not str(plain_pin).strip():
        raise ValueError("Mã PIN không được để trống.")
    salt = secrets.token_bytes(16)
    pin_bytes = str(plain_pin).strip().encode("utf-8")
    hash_bytes = hashlib.pbkdf2_hmac("sha256", pin_bytes, salt, 260_000)
    return f"{salt.hex()}${hash_bytes.hex()}"


def verify_pin(plain_pin: str, hashed_or_raw_pin: str) -> bool:
    """
    Verifies a plain PIN against a stored hash using constant-time comparison.
    Supports backwards-compatibility for plain text PINs during migration.
    """
    if not plain_pin or not hashed_or_raw_pin:
        return False
    plain_str = str(plain_pin).strip()
    stored_str = str(hashed_or_raw_pin).strip()

    if "$" in stored_str:
        try:
            salt_hex, hash_hex = stored_str.split("$", 1)
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
            computed_hash = hashlib.pbkdf2_hmac("sha256", plain_str.encode("utf-8"), salt, 260_000)
            return hmac.compare_digest(computed_hash, expected_hash)
        except Exception:
            return False
    # Fallback for plain-text PIN
    return hmac.compare_digest(plain_str, stored_str)


def revoke_token(token_or_jti: str, exp: Optional[int] = None) -> None:
    """Marks a JWT or JTI as revoked and purges any previously expired tokens."""
    now = int(time.time())
    # Prune expired tokens to avoid memory leak
    expired_jtis = [token_jti for token_jti, token_exp in _revoked_tokens_store.items() if token_exp < now]
    for ej in expired_jtis:
        _revoked_tokens_store.pop(ej, None)

    if exp is not None:
        _revoked_tokens_store[token_or_jti] = exp
        return

    # If full token was passed, decode payload to extract jti and exp
    try:
        payload = jwt.decode(token_or_jti, get_jwt_secret(), algorithms=["HS256"])
        jti = payload.get("jti")
        token_exp = payload.get("exp", now + 300)
        if jti:
            _revoked_tokens_store[jti] = token_exp
    except Exception:
        # Fallback if raw JTI was passed
        _revoked_tokens_store[token_or_jti] = now + 300


def is_token_revoked(jti: str) -> bool:
    """Checks whether the given JTI is in the revocation store."""
    now = int(time.time())
    if jti in _revoked_tokens_store:
        if _revoked_tokens_store[jti] >= now:
            return True
        # If already expired, remove it
        _revoked_tokens_store.pop(jti, None)
    return False


def create_kiosk_access_token(
    student_code: str,
    role: str = "STUDENT",
    kiosk_id: str = "KIOSK_LOBBY_H1",
    expires_delta_seconds: int = 300,
) -> str:
    """
    Issues a standardized HS256 JWT access token for a kiosk session.
    Payload: sub, role, kiosk_id, iat, exp, jti.
    """
    now = int(time.time())
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(student_code).strip(),
        "role": str(role).strip().upper(),
        "kiosk_id": kiosk_id,
        "iat": now,
        "exp": now + expires_delta_seconds,
        "jti": jti,
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm="HS256")
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT access token, verifying expiration, signature, and revocation status."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên làm việc (JWT) đã hết hạn. Vui lòng xác thực lại tại Kiosk.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã xác thực JWT không hợp lệ.",
        )

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên làm việc đã bị thu hồi (Logged out). Vui lòng đăng nhập lại.",
        )

    return payload


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> Dict[str, Any]:
    """FastAPI Dependency: Bắt buộc phải có JWT Bearer Token hợp lệ."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu tiêu đề Authorization: Bearer <token> để truy cập tài nguyên này.",
        )
    return decode_access_token(credentials.credentials)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> Optional[Dict[str, Any]]:
    """FastAPI Dependency: Cho phép người dùng vãng lai hoặc sinh viên đã đăng nhập."""
    if not credentials or not credentials.credentials:
        return None
    return decode_access_token(credentials.credentials)


def require_admin(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """FastAPI Dependency: Bắt buộc người dùng phải có quyền ADMIN (RBAC)."""
    if user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Từ chối truy cập: Endpoint này chỉ dành riêng cho Quản trị viên (ADMIN).",
        )
    return user


def assert_student_owner_or_admin(target_student_code: str, user: Dict[str, Any]) -> None:
    """
    Chống lỗi IDOR (Insecure Direct Object Reference):
    Chỉ cho phép sinh viên xem đúng dữ liệu của chính mình hoặc Admin xem toàn quyền.
    """
    user_role = user.get("role", "STUDENT")
    current_sub = str(user.get("sub", "")).strip().upper()
    target_clean = str(target_student_code).strip().upper()

    if user_role == "ADMIN":
        return

    if current_sub != target_clean:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Từ chối truy cập (Chống IDOR): Sinh viên '{current_sub}' không có quyền "
                f"xem hoặc thao tác trên hồ sơ học vụ của sinh viên '{target_clean}'."
            ),
        )

