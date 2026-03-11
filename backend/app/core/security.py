"""
Security utilities and rate limiting
"""
import re
import time
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Security Configuration
RATE_LIMIT_WINDOW = 300  # 5 minutes
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes
MAX_REGISTER_ATTEMPTS = 3

# Password requirements
MIN_PASSWORD_LENGTH = 8
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = True

# 2FA OTP Settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 3

# In-memory storage (use Redis in production)
login_attempts = defaultdict(list)
register_attempts = defaultdict(list)
locked_accounts = {}
otp_storage = {}


def generate_otp() -> str:
    """Generate a secure 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])


def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()


def store_otp(email: str, otp: str):
    """Store OTP with expiration"""
    otp_storage[email] = {
        "otp_hash": hash_token(otp),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0
    }


def verify_otp(email: str, otp: str) -> tuple:
    """Verify OTP and return (success, message)"""
    if email not in otp_storage:
        return False, "No OTP found. Please request a new one."
    
    stored = otp_storage[email]
    
    if datetime.now(timezone.utc) > stored["expires_at"]:
        del otp_storage[email]
        return False, "OTP has expired. Please request a new one."
    
    if stored["attempts"] >= MAX_OTP_ATTEMPTS:
        del otp_storage[email]
        return False, "Too many failed attempts. Please request a new OTP."
    
    if hash_token(otp) != stored["otp_hash"]:
        otp_storage[email]["attempts"] += 1
        remaining = MAX_OTP_ATTEMPTS - otp_storage[email]["attempts"]
        return False, f"Invalid OTP. {remaining} attempts remaining."
    
    del otp_storage[email]
    return True, "OTP verified successfully"


def is_account_locked(email: str) -> bool:
    """Check if account is locked due to too many failed attempts"""
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
    """Record a login attempt for rate limiting"""
    current_time = time.time()
    login_attempts[email] = [
        (ts, s) for ts, s in login_attempts[email] 
        if current_time - ts < RATE_LIMIT_WINDOW
    ]
    login_attempts[email].append((current_time, success))
    
    failed_attempts = [a for a in login_attempts[email] if not a[1]]
    if len(failed_attempts) >= MAX_LOGIN_ATTEMPTS:
        locked_accounts[email] = current_time + LOCKOUT_DURATION
        login_attempts[email] = []


def check_registration_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded registration rate limit"""
    current_time = time.time()
    register_attempts[ip] = [
        ts for ts in register_attempts[ip] 
        if current_time - ts < RATE_LIMIT_WINDOW
    ]
    return len(register_attempts[ip]) < MAX_REGISTER_ATTEMPTS


def record_registration_attempt(ip: str):
    """Record a registration attempt"""
    register_attempts[ip].append(time.time())


def validate_password_strength(password: str) -> tuple:
    """Validate password meets security requirements"""
    errors = []
    
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"at least {MIN_PASSWORD_LENGTH} characters")
    
    if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("one uppercase letter")
    
    if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("one lowercase letter")
    
    if REQUIRE_DIGIT and not re.search(r'\d', password):
        errors.append("one digit")
    
    if REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~]', password):
        errors.append("one special character (!@#$%^&*)")
    
    if errors:
        return False, f"Password must contain: {', '.join(errors)}"
    
    weak_patterns = ['password', '123456', 'qwerty', 'admin', 'letmein', 'welcome']
    if any(pattern in password.lower() for pattern in weak_patterns):
        return False, "Password contains common weak patterns"
    
    return True, "Password is strong"


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return text
    dangerous_chars = ['$', '{', '}']
    for char in dangerous_chars:
        text = text.replace(char, '')
    return text.strip()


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)
