"""
Authentication Routes - Handles all auth-related endpoints
- Register, Login, Logout
- Email Verification
- 2FA (OTP)
- Password Management (change, forgot, reset)
- Session Exchange (OAuth)
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime, timezone, timedelta
import asyncio
import uuid
import logging
import httpx

from app.database import db
from app.config import OTP_EXPIRY_MINUTES
from app.services.security import (
    hash_password, verify_password, create_jwt_token,
    generate_otp, store_otp, verify_otp,
    is_account_locked, get_lockout_remaining, record_login_attempt,
    check_registration_rate_limit, record_registration_attempt,
    validate_password_strength, sanitize_input,
    generate_secure_token, hash_token
)
from app.services.email_service import send_email_async, send_admin_notification, send_verification_email
from app.models.user import (
    UserRole, UserCreate, UserResponse, LoginRequest, TokenResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    EmailVerificationRequest, OTPVerifyRequest, TwoFactorToggle
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============== HELPER: Get Current User ==============
async def get_current_user(request: Request) -> dict:
    """Extract and validate user from JWT token"""
    import jwt
    from app.config import JWT_SECRET, JWT_ALGORITHM
    
    auth_header = request.headers.get("Authorization", "")
    session_token = request.cookies.get("session_token")
    
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif session_token:
        session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
        if session:
            user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
            if user:
                return user
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============== REGISTER ==============
@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, request: Request):
    """Register a new user"""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Check registration rate limit
    if not check_registration_rate_limit(client_ip):
        logger.warning(f"Registration rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail="Too many registration attempts. Please try again in 5 minutes."
        )
    
    record_registration_attempt(client_ip)
    
    email = sanitize_input(user_data.email.lower().strip())
    name = sanitize_input(user_data.name)
    
    # Check if email already exists
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate email verification token
    verification_token = generate_secure_token(32)
    verification_token_hash = hash_token(verification_token)
    verification_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    
    user_doc = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "role": user_data.role,
        "password_hash": hash_password(user_data.password),
        "picture": None,
        "company_name": None,
        "email_verified": False,
        "verification_token_hash": verification_token_hash,
        "verification_expires": verification_expires,
        "created_at": now,
        "last_login": now,
        "login_count": 1,
        "failed_login_attempts": 0,
        "security_settings": {
            "two_factor_enabled": False,
            "password_changed_at": now
        }
    }
    
    await db.users.insert_one(user_doc)
    
    # Send verification email
    asyncio.create_task(send_verification_email(email, name, verification_token))
    
    logger.info(f"New user registered: {email} (ID: {user_id}) from IP: {client_ip}")
    
    # Send admin notification
    asyncio.create_task(send_admin_notification("new_user", {
        "name": name,
        "email": email,
        "role": user_data.role,
        "company_name": user_data.company_name if user_data.role == "vendor" else "N/A",
        "created_at": now
    }))
    
    # Create vendor profile if needed
    vendor_company_name = None
    if user_data.role == "vendor" and user_data.company_name:
        vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
        vendor_doc = {
            "vendor_id": vendor_id,
            "user_id": user_id,
            "company_name": user_data.company_name,
            "trade_name": getattr(user_data, 'trade_name', '') or "",
            "gstin": user_data.gstin or "",
            "address": user_data.address or "",
            "country": user_data.country or "India",
            "city": user_data.city or "",
            "state": user_data.state or "",
            "pincode": user_data.pincode or "",
            "phone": user_data.phone or "",
            "description": "",
            "website": "",
            "certifications": [],
            "industries": [],
            "materials_handled": [],
            "is_approved": False,
            "rating": 0,
            "total_jobs": 0,
            "created_at": now,
            "updated_at": now
        }
        await db.vendors.insert_one(vendor_doc)
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"company_name": user_data.company_name}}
        )
        vendor_company_name = user_data.company_name
        logger.info(f"Vendor profile created for {email} (Vendor ID: {vendor_id})")
    
    token = create_jwt_token(user_id, email, user_data.role)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            user_id=user_id,
            email=email,
            name=name,
            role=user_data.role,
            picture=None,
            company_name=vendor_company_name,
            email_verified=False,
            created_at=user_doc["created_at"]
        )
    )


# ============== EMAIL VERIFICATION ==============
@router.post("/verify-email")
async def verify_email(verification_data: EmailVerificationRequest):
    """Verify user's email address using token from email"""
    token_hash = hash_token(verification_data.token)
    
    user = await db.users.find_one({"verification_token_hash": token_hash}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    
    if user.get("email_verified"):
        return {"message": "Email already verified", "already_verified": True}
    
    # Check expiration
    expires_at = user.get("verification_expires")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Verification link has expired. Please request a new one.")
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {"email_verified": True},
            "$unset": {"verification_token_hash": "", "verification_expires": ""}
        }
    )
    
    logger.info(f"Email verified for user: {user['email']}")
    return {"message": "Email verified successfully", "email": user["email"]}


@router.post("/resend-verification")
async def resend_verification_email_route(user: dict = Depends(get_current_user)):
    """Resend verification email to current user"""
    if user.get("email_verified"):
        return {"message": "Email already verified"}
    
    verification_token = generate_secure_token(32)
    verification_token_hash = hash_token(verification_token)
    verification_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {
                "verification_token_hash": verification_token_hash,
                "verification_expires": verification_expires
            }
        }
    )
    
    asyncio.create_task(send_verification_email(user["email"], user["name"], verification_token))
    logger.info(f"Verification email resent to: {user['email']}")
    
    return {"message": "Verification email sent. Please check your inbox."}


# ============== LOGIN ==============
@router.post("/login")
async def login(login_data: LoginRequest, request: Request):
    """Login with email and password"""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    email = sanitize_input(login_data.email.lower().strip())
    
    # Check if account is locked
    if is_account_locked(email):
        remaining = get_lockout_remaining(email)
        logger.warning(f"Login attempt on locked account: {email} from IP: {client_ip}")
        raise HTTPException(
            status_code=423, 
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {remaining // 60} minutes."
        )
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if not user:
        record_login_attempt(email, False)
        logger.warning(f"Failed login attempt for non-existent email: {email} from IP: {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(login_data.password, user.get("password_hash", "")):
        record_login_attempt(email, False)
        await db.users.update_one(
            {"email": email},
            {"$inc": {"failed_login_attempts": 1}}
        )
        logger.warning(f"Failed login attempt for: {email} from IP: {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if 2FA is enabled
    security_settings = user.get("security_settings", {})
    two_factor_enabled = security_settings.get("two_factor_enabled", False)
    
    if two_factor_enabled:
        otp = generate_otp()
        store_otp(email, otp)
        
        otp_html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1e40af;">Your Login Verification Code</h2>
            <p>Hello {user.get("name", "User")},</p>
            <p>Your one-time verification code is:</p>
            <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin: 20px 0; text-align: center;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1e40af;">{otp}</span>
            </div>
            <p style="color: #666;">This code expires in {OTP_EXPIRY_MINUTES} minutes.</p>
            <p style="color: #dc2626; font-size: 14px;"><strong>If you didn't request this code, please ignore this email.</strong></p>
        </div>
        '''
        asyncio.create_task(send_email_async(email, "Your OEMLinker Login Code", otp_html))
        
        logger.info(f"2FA OTP sent to: {email} from IP: {client_ip}")
        
        return {
            "requires_2fa": True,
            "message": "Verification code sent to your email",
            "email_hint": f"{email[:3]}***{email[email.index('@'):]}"
        }
    
    # No 2FA - proceed with normal login
    record_login_attempt(email, True)
    
    await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "last_login": datetime.now(timezone.utc).isoformat(),
                "last_login_ip": client_ip,
                "failed_login_attempts": 0
            },
            "$inc": {"login_count": 1}
        }
    )
    
    logger.info(f"Successful login: {email} from IP: {client_ip}")
    
    token = create_jwt_token(user["user_id"], user["email"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            picture=user.get("picture"),
            company_name=user.get("company_name"),
            email_verified=user.get("email_verified", False),
            created_at=user["created_at"]
        )
    )


# ============== 2FA ENDPOINTS ==============
class OTPVerifyRequestLocal(BaseModel):
    email: EmailStr
    otp: str
    password: str


@router.post("/verify-otp")
async def verify_otp_endpoint(otp_data: OTPVerifyRequestLocal, request: Request):
    """Verify OTP and complete login"""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    email = sanitize_input(otp_data.email.lower().strip())
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(otp_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    success, message = verify_otp(email, otp_data.otp)
    if not success:
        logger.warning(f"Failed OTP verification for: {email} from IP: {client_ip} - {message}")
        raise HTTPException(status_code=400, detail=message)
    
    record_login_attempt(email, True)
    
    await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "last_login": datetime.now(timezone.utc).isoformat(),
                "last_login_ip": client_ip,
                "failed_login_attempts": 0
            },
            "$inc": {"login_count": 1}
        }
    )
    
    logger.info(f"Successful 2FA login: {email} from IP: {client_ip}")
    
    token = create_jwt_token(user["user_id"], user["email"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            picture=user.get("picture"),
            company_name=user.get("company_name"),
            email_verified=user.get("email_verified", False),
            created_at=user["created_at"]
        )
    )


@router.post("/resend-otp")
async def resend_otp(request: Request):
    """Resend OTP for 2FA"""
    body = await request.json()
    email = sanitize_input(body.get("email", "").lower().strip())
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        return {"message": "If an account exists, a new code has been sent."}
    
    otp = generate_otp()
    store_otp(email, otp)
    
    otp_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1e40af;">Your New Login Verification Code</h2>
        <p>Hello {user.get("name", "User")},</p>
        <p>Your new one-time verification code is:</p>
        <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin: 20px 0; text-align: center;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1e40af;">{otp}</span>
        </div>
        <p style="color: #666;">This code expires in {OTP_EXPIRY_MINUTES} minutes.</p>
    </div>
    '''
    asyncio.create_task(send_email_async(email, "Your New OEMLinker Login Code", otp_html))
    
    return {"message": "A new verification code has been sent to your email."}


class TwoFactorToggleLocal(BaseModel):
    enable: bool
    password: str


@router.post("/2fa/toggle")
async def toggle_2fa(
    toggle_data: TwoFactorToggleLocal, 
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Enable or disable 2FA for the user"""
    client_ip = request.client.host if request.client else "unknown"
    
    db_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not db_user or not verify_password(toggle_data.password, db_user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Invalid password")
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"security_settings.two_factor_enabled": toggle_data.enable}}
    )
    
    action = "enabled" if toggle_data.enable else "disabled"
    
    alert_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: {'#f0fdf4' if toggle_data.enable else '#fef2f2'}; border-left: 4px solid {'#22c55e' if toggle_data.enable else '#ef4444'}; padding: 16px; margin-bottom: 20px;">
            <h2 style="color: {'#166534' if toggle_data.enable else '#dc2626'}; margin: 0 0 8px 0;">Two-Factor Authentication {action.capitalize()}</h2>
        </div>
        <p>Hello {db_user.get("name", "User")},</p>
        <p>Two-factor authentication has been <strong>{action}</strong> for your OEMLinker account.</p>
    </div>
    '''
    asyncio.create_task(send_email_async(user["email"], f"2FA {action.capitalize()} - Security Update", alert_html))
    
    logger.info(f"2FA {action} for user: {user['email']} from IP: {client_ip}")
    
    return {"message": f"Two-factor authentication has been {action}", "two_factor_enabled": toggle_data.enable}


@router.get("/2fa/status")
async def get_2fa_status(user: dict = Depends(get_current_user)):
    """Get current 2FA status for the user"""
    db_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    security_settings = db_user.get("security_settings", {}) if db_user else {}
    
    return {
        "two_factor_enabled": security_settings.get("two_factor_enabled", False),
        "password_changed_at": security_settings.get("password_changed_at")
    }


# ============== SESSION / OAUTH ==============
@router.post("/session")
async def exchange_session(request: Request, response: Response):
    """Exchange Emergent Auth session_id for session data"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        session_data = resp.json()
    
    email = session_data["email"]
    name = session_data["name"]
    picture = session_data.get("picture")
    session_token = session_data["session_token"]
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user:
        user_id = user["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "role": UserRole.BUYER,
            "picture": picture,
            "password_hash": None,
            "company_name": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)
    
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )
    
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    return {
        "user_id": user_doc["user_id"],
        "email": user_doc["email"],
        "name": user_doc["name"],
        "role": user_doc["role"],
        "picture": user_doc.get("picture"),
        "company_name": user_doc.get("company_name"),
        "created_at": user_doc["created_at"]
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "picture": user.get("picture"),
        "company_name": user.get("company_name"),
        "email_verified": user.get("email_verified", False),
        "created_at": user["created_at"]
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}


# ============== PASSWORD MANAGEMENT ==============
class PasswordChangeRequestLocal(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v


class PasswordResetRequestLocal(BaseModel):
    email: EmailStr


class PasswordResetConfirmLocal(BaseModel):
    token: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequestLocal, 
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Change password for authenticated user"""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    db_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(password_data.current_password, db_user.get("password_hash", "")):
        logger.warning(f"Failed password change attempt for user: {user['email']}")
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if password_data.current_password == password_data.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")
    
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {
                "password_hash": hash_password(password_data.new_password),
                "security_settings.password_changed_at": now.isoformat()
            }
        }
    )
    
    alert_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 16px; margin-bottom: 20px;">
            <h2 style="color: #dc2626; margin: 0 0 8px 0;">Security Alert</h2>
            <p style="color: #7f1d1d; margin: 0;">Your password was changed</p>
        </div>
        <p>Hello {db_user.get("name", "User")},</p>
        <p>Your OEMLinker account password was successfully changed.</p>
        <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px 0;"><strong>Time:</strong> {now.strftime("%B %d, %Y at %I:%M %p UTC")}</p>
            <p style="margin: 0;"><strong>IP Address:</strong> {client_ip}</p>
        </div>
        <p style="color: #dc2626; font-weight: bold;">If you did not make this change, please reset your password immediately.</p>
    </div>
    '''
    asyncio.create_task(send_email_async(user["email"], "Password Changed - Security Alert", alert_html))
    
    logger.info(f"Password changed successfully for user: {user['email']} from IP: {client_ip}")
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(reset_request: PasswordResetRequestLocal, request: Request):
    """Request password reset email"""
    client_ip = request.client.host if request.client else "unknown"
    email = sanitize_input(reset_request.email.lower().strip())
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user:
        reset_token = generate_secure_token(32)
        token_hash = hash_token(reset_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        await db.password_resets.delete_many({"email": email})
        await db.password_resets.insert_one({
            "email": email,
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "used": False
        })
        
        reset_link = f"https://oemlinker.com/reset-password?token={reset_token}"
        
        email_html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1e40af;">Password Reset Request</h2>
            <p>Hello {user.get("name", "User")},</p>
            <p>We received a request to reset your password. Click the button below to reset (expires in 1 hour).</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #f97316; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Reset Password</a>
            </div>
            <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
        </div>
        '''
        
        asyncio.create_task(send_email_async(email, "Reset Your OEMLinker Password", email_html))
        logger.info(f"Password reset requested for: {email} from IP: {client_ip}")
    else:
        logger.warning(f"Password reset requested for non-existent email: {email} from IP: {client_ip}")
    
    return {"message": "If an account exists with that email, you will receive a password reset link shortly."}


@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirmLocal, request: Request):
    """Reset password using token from email"""
    from app.config import locked_accounts
    
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    token_hash = hash_token(reset_data.token)
    
    reset_record = await db.password_resets.find_one({
        "token_hash": token_hash,
        "used": False
    }, {"_id": 0})
    
    if not reset_record:
        logger.warning(f"Invalid password reset token attempt from IP: {client_ip}")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    expires_at = datetime.fromisoformat(reset_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        await db.password_resets.delete_one({"token_hash": token_hash})
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")
    
    email = reset_record["email"]
    
    db_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    now = datetime.now(timezone.utc)
    result = await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "password_hash": hash_password(reset_data.new_password),
                "failed_login_attempts": 0,
                "security_settings.password_changed_at": now.isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.password_resets.update_one(
        {"token_hash": token_hash},
        {"$set": {"used": True}}
    )
    
    if email in locked_accounts:
        del locked_accounts[email]
    
    user_name = db_user.get("name", "User") if db_user else "User"
    alert_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 16px; margin-bottom: 20px;">
            <h2 style="color: #dc2626; margin: 0 0 8px 0;">Security Alert</h2>
            <p style="color: #7f1d1d; margin: 0;">Your password was reset</p>
        </div>
        <p>Hello {user_name},</p>
        <p>Your OEMLinker account password was successfully reset.</p>
        <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px 0;"><strong>Time:</strong> {now.strftime("%B %d, %Y at %I:%M %p UTC")}</p>
            <p style="margin: 0;"><strong>IP Address:</strong> {client_ip}</p>
        </div>
        <p style="color: #dc2626; font-weight: bold;">If you did not request this password reset, contact support immediately.</p>
    </div>
    '''
    asyncio.create_task(send_email_async(email, "Password Reset - Security Alert", alert_html))
    
    logger.info(f"Password reset successfully for: {email} from IP: {client_ip}")
    return {"message": "Password has been reset successfully. You can now log in with your new password."}


@router.put("/role")
async def update_role(request: Request, user: dict = Depends(get_current_user)):
    """Update user role"""
    body = await request.json()
    new_role = body.get("role")
    
    if new_role not in [UserRole.BUYER, UserRole.VENDOR]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"role": new_role}}
    )
    
    return {"message": "Role updated", "role": new_role}


# ============== MAGIC LINK ENDPOINTS ==============
@router.post("/magic-link/generate")
async def generate_magic_link(phone: str, redirect_url: Optional[str] = None):
    """Generate a magic link token for WhatsApp users (internal use only)
    
    Args:
        phone: User's phone number
        redirect_url: Optional URL to redirect to after successful login (e.g., /vendor/rfq/rfq_123)
    """
    import secrets
    
    # Normalize phone
    phone_normalized = phone.replace("+", "").replace(" ", "").replace("-", "")
    phone_10digit = phone_normalized[-10:] if len(phone_normalized) >= 10 else phone_normalized
    
    # Find vendor by phone
    vendor = await db.vendors.find_one(
        {"phone": {"$regex": phone_10digit}},
        {"_id": 0, "user_id": 1, "vendor_id": 1}
    )
    
    if not vendor:
        return {"success": False, "error": "Vendor not found"}
    
    user = await db.users.find_one({"user_id": vendor["user_id"]}, {"_id": 0})
    if not user:
        return {"success": False, "error": "User not found"}
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)  # 30 min expiry for RFQ links
    
    # Validate and sanitize redirect URL - only allow internal paths
    safe_redirect = None
    if redirect_url:
        # Only allow relative paths starting with /
        if redirect_url.startswith("/") and not redirect_url.startswith("//"):
            # Whitelist of allowed redirect patterns
            allowed_patterns = [
                "/vendor/", "/buyer/", "/admin/", "/dashboard", "/rfq/", "/quotes", "/orders"
            ]
            if any(redirect_url.startswith(pattern) or pattern in redirect_url for pattern in allowed_patterns):
                safe_redirect = redirect_url
    
    # Store token in MongoDB with redirect URL
    await db.magic_link_tokens.insert_one({
        "token": token,
        "user_id": user["user_id"],
        "phone": phone_normalized,
        "redirect_url": safe_redirect,  # Store validated redirect URL
        "expires_at": expires_at.isoformat(),
        "used": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Clean up expired tokens periodically
    await db.magic_link_tokens.delete_many({
        "expires_at": {"$lt": datetime.now(timezone.utc).isoformat()}
    })
    
    return {
        "success": True,
        "token": token,
        "expires_in_minutes": 30,
        "redirect_url": safe_redirect
    }


@router.get("/magic-link/verify/{token}")
async def verify_magic_link(token: str, response: Response):
    """Verify magic link token and create session"""
    import secrets
    from app.services.security import create_jwt_token
    
    # Find token in MongoDB
    token_doc = await db.magic_link_tokens.find_one({"token": token}, {"_id": 0})
    
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired link")
    
    # Check expiry
    expires_at = datetime.fromisoformat(token_doc["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if datetime.now(timezone.utc) > expires_at:
        await db.magic_link_tokens.delete_one({"token": token})
        raise HTTPException(status_code=400, detail="Link has expired. Please request a new one via WhatsApp.")
    
    # Check if already used
    if token_doc.get("used"):
        raise HTTPException(status_code=400, detail="Link has already been used. Please request a new one via WhatsApp.")
    
    # Mark as used atomically
    result = await db.magic_link_tokens.update_one(
        {"token": token, "used": False},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Link has already been used. Please request a new one via WhatsApp.")
    
    # Get user
    user = await db.users.find_one({"user_id": token_doc["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create JWT token
    jwt_token = create_jwt_token(user["user_id"], user["email"], user["role"])
    
    # Create session
    session_token = secrets.token_urlsafe(32)
    await db.user_sessions.insert_one({
        "user_id": user["user_id"],
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "login_method": "magic_link"
    })
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )
    
    # Update last login
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}, "$inc": {"login_count": 1}}
    )
    
    # Get redirect URL from token (if set)
    redirect_url = token_doc.get("redirect_url") or f"/{user['role']}/dashboard"
    
    # Delete used token
    await db.magic_link_tokens.delete_one({"token": token})
    
    return {
        "success": True,
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "picture": user.get("picture"),
            "company_name": user.get("company_name"),
            "email_verified": user.get("email_verified", False),
            "phone_login": user.get("phone_login", False)
        },
        "redirect_url": redirect_url
    }
