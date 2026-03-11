"""
Core module - Security, Auth, and common utilities
"""
from app.core.security import (
    generate_otp,
    store_otp,
    verify_otp,
    is_account_locked,
    get_lockout_remaining,
    record_login_attempt,
    check_registration_rate_limit,
    record_registration_attempt,
    validate_password_strength,
    sanitize_input,
    generate_secure_token,
    hash_token,
)

from app.core.auth import (
    hash_password,
    verify_password,
    create_jwt_token,
    decode_jwt_token,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
)

__all__ = [
    # Security
    "generate_otp",
    "store_otp",
    "verify_otp",
    "is_account_locked",
    "get_lockout_remaining",
    "record_login_attempt",
    "check_registration_rate_limit",
    "record_registration_attempt",
    "validate_password_strength",
    "sanitize_input",
    "generate_secure_token",
    "hash_token",
    # Auth
    "hash_password",
    "verify_password",
    "create_jwt_token",
    "decode_jwt_token",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "JWT_EXPIRATION_HOURS",
]
