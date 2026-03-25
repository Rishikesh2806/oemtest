"""
Security-related utilities: Password hashing, JWT, rate limiting
"""
import bcrypt
import jwt
import secrets
import hashlib
import time
import re
from datetime import datetime, timezone, timedelta
from app.config import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS,
    RATE_LIMIT_WINDOW, MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION,
    MAX_REGISTER_ATTEMPTS, OTP_LENGTH, OTP_EXPIRY_MINUTES, MAX_OTP_ATTEMPTS,
    MIN_PASSWORD_LENGTH, REQUIRE_UPPERCASE, REQUIRE_LOWERCASE,
    REQUIRE_DIGIT, REQUIRE_SPECIAL,
    login_attempts, register_attempts, locked_accounts, otp_storage
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_jwt_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token for authentication"""
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def generate_otp() -> str:
    """Generate a secure 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])


def store_otp(email: str, otp: str):
    """Store OTP with expiry"""
    otp_storage[email] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0
    }


def verify_otp(email: str, otp: str) -> tuple:
    """Verify OTP and return (success, message)"""
    if email not in otp_storage:
        return False, "No OTP found. Please request a new one."
    
    stored = otp_storage[email]
    
    # Check expiry
    if datetime.now(timezone.utc) > stored["expires_at"]:
        del otp_storage[email]
        return False, "OTP has expired. Please request a new one."
    
    # Check attempts
    if stored["attempts"] >= MAX_OTP_ATTEMPTS:
        del otp_storage[email]
        return False, "Too many failed attempts. Please request a new OTP."
    
    # Verify OTP
    if stored["otp"] != otp:
        otp_storage[email]["attempts"] += 1
        remaining = MAX_OTP_ATTEMPTS - otp_storage[email]["attempts"]
        return False, f"Invalid OTP. {remaining} attempts remaining."
    
    # Success - clean up
    del otp_storage[email]
    return True, "OTP verified successfully"


def is_account_locked(email: str) -> bool:
    """Check if account is locked due to failed login attempts"""
    if email in locked_accounts:
        if time.time() < locked_accounts[email]:
            return True
        else:
            del locked_accounts[email]
    return False


def get_lockout_remaining(email: str) -> int:
    """Get remaining lockout time in seconds"""
    if email in locked_accounts:
        remaining = int(locked_accounts[email] - time.time())
        return max(0, remaining)
    return 0


def record_login_attempt(email: str, success: bool):
    """Record login attempt and lock account if needed"""
    current_time = time.time()
    
    # Clean old attempts
    login_attempts[email] = [
        (ts, s) for ts, s in login_attempts[email]
        if current_time - ts < RATE_LIMIT_WINDOW
    ]
    
    login_attempts[email].append((current_time, success))
    
    if not success:
        failed_attempts = sum(1 for ts, s in login_attempts[email] if not s)
        if failed_attempts >= MAX_LOGIN_ATTEMPTS:
            locked_accounts[email] = current_time + LOCKOUT_DURATION


def check_registration_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded registration rate limit"""
    current_time = time.time()
    register_attempts[ip] = [
        ts for ts in register_attempts[ip]
        if current_time - ts < RATE_LIMIT_WINDOW
    ]
    return len(register_attempts[ip]) < MAX_REGISTER_ATTEMPTS


def record_registration_attempt(ip: str):
    """Record registration attempt"""
    register_attempts[ip].append(time.time())


def validate_password_strength(password: str) -> tuple:
    """Validate password meets security requirements"""
    errors = []
    
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    
    if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if REQUIRE_DIGIT and not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
        errors.append("Password must contain at least one special character")
    
    # Check for common patterns
    common_patterns = ['password', '123456', 'qwerty', 'abc123', 'letmein']
    if password.lower() in common_patterns:
        errors.append("Password is too common")
    
    if errors:
        return False, "; ".join(errors)
    return True, "Password meets requirements"


def sanitize_input(text: str) -> str:
    """Basic input sanitization"""
    if not text:
        return text
    # Remove potential script tags and SQL injection patterns
    dangerous_patterns = ['<script', '</script', 'javascript:', 'onclick', 'onerror']
    result = text
    for pattern in dangerous_patterns:
        result = result.replace(pattern, '')
    return result.strip()


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()
