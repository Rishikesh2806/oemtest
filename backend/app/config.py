"""
Application Configuration and Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# ============== DATABASE ==============
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# ============== JWT SETTINGS ==============
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'offloadex_secret_key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 168  # 7 days

# ============== SECURITY SETTINGS ==============
# Rate limiting configuration
RATE_LIMIT_WINDOW = 300  # 5 minutes
MAX_LOGIN_ATTEMPTS = 5  # Max failed login attempts before lockout
LOCKOUT_DURATION = 900  # 15 minutes lockout
MAX_REGISTER_ATTEMPTS = 3  # Max registration attempts per IP per window

# Password requirements
MIN_PASSWORD_LENGTH = 8
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = True

# ============== 2FA OTP SETTINGS ==============
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 3

# ============== EMAIL SETTINGS ==============
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
APP_URL = os.environ.get("APP_URL", "https://rfq-marketplace-9.preview.emergentagent.com")
ADMIN_EMAIL = "oemlinker@gmail.com"
FROM_EMAIL = "OEMLinker <notifications@oemlinker.com>"

# ============== GSTIN API ==============
GSTIN_API_KEY = os.environ.get("GSTIN_API_KEY")

# ============== IN-MEMORY STORAGE (Use Redis in production) ==============
login_attempts = defaultdict(list)  # {email: [(timestamp, success), ...]}
register_attempts = defaultdict(list)  # {ip: [timestamp, ...]}
locked_accounts = {}  # {email: unlock_timestamp}
otp_storage = {}  # {email: {"otp": str, "expires_at": datetime, "attempts": int}}
