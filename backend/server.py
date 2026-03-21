from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import base64
import aiofiles
import httpx
import asyncio
import resend
import re
import secrets
import hashlib
from collections import defaultdict
import time
from io import BytesIO
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Voice Agent imports
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech, LlmChat, UserMessage

# ============== MODULAR IMPORTS (NEW) ==============
# Import from new modular structure for reusability
# The application is being gradually refactored into modules
# See ARCHITECTURE.md for details on the refactoring plan
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Core utilities - Security, Auth, Validation
from app.core import (
    hash_token, generate_secure_token, sanitize_input,
    validate_password_strength, generate_otp, store_otp, verify_otp,
    is_account_locked, get_lockout_remaining,
    record_login_attempt, check_registration_rate_limit, record_registration_attempt
)

# Models are still defined in server.py but can also be imported from:
# from app.models import UserRole, UserResponse, VendorProfile, etc.

# Services provide business logic (use these for new code):
# from app.services import get_user_by_id, create_vendor_profile, etc.

# Dependencies for route handlers:
# from app.dependencies import get_current_user, require_admin, etc.
# ===================================================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
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

# In-memory rate limiting storage (use Redis in production)
login_attempts = defaultdict(list)  # {email: [(timestamp, success), ...]}
register_attempts = defaultdict(list)  # {ip: [timestamp, ...]}
locked_accounts = {}  # {email: unlock_timestamp}

# 2FA OTP Settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
otp_storage = {}  # {email: {"otp": str, "expires_at": datetime, "attempts": int}}
MAX_OTP_ATTEMPTS = 3

def generate_otp() -> str:
    """Generate a secure 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])

def store_otp(email: str, otp: str):
    """Store OTP with expiration"""
    otp_storage[email] = {
        "otp_hash": hash_token(otp),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0
    }

def verify_otp(email: str, otp: str) -> tuple[bool, str]:
    """Verify OTP and return (success, message)"""
    if email not in otp_storage:
        return False, "No OTP found. Please request a new one."
    
    stored = otp_storage[email]
    
    # Check expiration
    if datetime.now(timezone.utc) > stored["expires_at"]:
        del otp_storage[email]
        return False, "OTP has expired. Please request a new one."
    
    # Check attempts
    if stored["attempts"] >= MAX_OTP_ATTEMPTS:
        del otp_storage[email]
        return False, "Too many failed attempts. Please request a new OTP."
    
    # Verify OTP
    if hash_token(otp) != stored["otp_hash"]:
        otp_storage[email]["attempts"] += 1
        remaining = MAX_OTP_ATTEMPTS - otp_storage[email]["attempts"]
        return False, f"Invalid OTP. {remaining} attempts remaining."
    
    # Success - remove OTP
    del otp_storage[email]
    return True, "OTP verified successfully"

# Security utility functions
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
    # Clean old attempts
    login_attempts[email] = [
        (ts, s) for ts, s in login_attempts[email] 
        if current_time - ts < RATE_LIMIT_WINDOW
    ]
    login_attempts[email].append((current_time, success))
    
    # Check for lockout
    failed_attempts = [a for a in login_attempts[email] if not a[1]]
    if len(failed_attempts) >= MAX_LOGIN_ATTEMPTS:
        locked_accounts[email] = current_time + LOCKOUT_DURATION
        login_attempts[email] = []  # Reset attempts after lockout

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

def validate_password_strength(password: str) -> tuple[bool, str]:
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
    
    # Check for common weak patterns
    weak_patterns = ['password', '123456', 'qwerty', 'admin', 'letmein', 'welcome']
    if any(pattern in password.lower() for pattern in weak_patterns):
        return False, "Password contains common weak patterns"
    
    return True, "Password is strong"

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return text
    # Remove potentially dangerous characters for NoSQL injection
    dangerous_chars = ['$', '{', '}']
    for char in dangerous_chars:
        text = text.replace(char, '')
    return text.strip()

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)

def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()

# Create the main app
app = FastAPI(title="OEMLinker API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== EMAIL SERVICE ==============

# Initialize Resend
resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

async def send_email_async(to_email: str, subject: str, html_content: str):
    """Send email asynchronously using Resend"""
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return None
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return None

# Admin notification email
ADMIN_EMAIL = "oemlinker@gmail.com"

async def send_admin_notification(event_type: str, data: dict):
    """Send notification email to admin for important platform events"""
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not configured, skipping admin notification")
        return None
    
    templates = {
        "new_user": {
            "subject": f"👤 New User Registration: {data.get('name', 'Unknown')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">New User Registration</h2>
                </div>
                <div style="padding: 25px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;"><strong>A new user has registered on OEMLinker:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Name:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">{data.get('name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Email:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('email', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Role:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('role', 'N/A').upper()}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Company:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('company_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; color: #64748b;">Registered At:</td><td style="padding: 8px;">{data.get('created_at', 'N/A')}</td></tr>
                    </table>
                </div>
            </div>
            """
        },
        "new_rfq": {
            "subject": f"📋 New RFQ Created: {data.get('title', 'Untitled')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #059669 0%, #047857 100%); padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">New RFQ Created</h2>
                </div>
                <div style="padding: 25px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;"><strong>A new RFQ has been submitted:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">RFQ ID:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{data.get('rfq_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Title:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">{data.get('title', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Buyer:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('buyer_name', 'N/A')} ({data.get('buyer_email', 'N/A')})</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Material:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('material_type', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Quantity:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('quantity', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; color: #64748b;">Created At:</td><td style="padding: 8px;">{data.get('created_at', 'N/A')}</td></tr>
                    </table>
                </div>
            </div>
            """
        },
        "new_quotation": {
            "subject": f"💰 New Quotation Submitted: ₹{data.get('total_amount', 0):,.2f}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">New Quotation Submitted</h2>
                </div>
                <div style="padding: 25px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;"><strong>A vendor has submitted a quotation:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Quote ID:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{data.get('quote_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">RFQ Title:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('rfq_title', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Vendor:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('vendor_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Buyer:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('buyer_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Amount:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: #059669;">₹{data.get('total_amount', 0):,.2f}</td></tr>
                        <tr><td style="padding: 8px; color: #64748b;">Lead Time:</td><td style="padding: 8px;">{data.get('lead_time', 'N/A')} days</td></tr>
                    </table>
                </div>
            </div>
            """
        },
        "vendor_matching": {
            "subject": f"🎯 Vendor Matching Complete: {data.get('matched_count', 0)} vendors for {data.get('rfq_title', 'RFQ')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">Vendor Matching Complete</h2>
                </div>
                <div style="padding: 25px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;"><strong>AI matching has found suitable vendors:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">RFQ ID:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{data.get('rfq_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Title:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('rfq_title', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Buyer:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('buyer_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Matched Vendors:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: #f97316;">{data.get('matched_count', 0)}</td></tr>
                        <tr><td style="padding: 8px; color: #64748b;">Top Match:</td><td style="padding: 8px;">{data.get('top_vendor', 'N/A')} ({data.get('top_score', 0)}%)</td></tr>
                    </table>
                </div>
            </div>
            """
        },
        "quotation_accepted": {
            "subject": f"✅ Quotation Accepted: ₹{data.get('total_amount', 0):,.2f} - PO #{data.get('po_number', 'N/A')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">Quotation Accepted - PO Created</h2>
                </div>
                <div style="padding: 25px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;"><strong>A buyer has accepted a quotation:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">PO Number:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: #16a34a;">{data.get('po_number', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Order ID:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{data.get('order_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">RFQ Title:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('rfq_title', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Buyer:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('buyer_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Vendor:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('vendor_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Amount:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; font-size: 18px; color: #16a34a;">₹{data.get('total_amount', 0):,.2f}</td></tr>
                        <tr><td style="padding: 8px; color: #64748b;">Payment Terms:</td><td style="padding: 8px;">{data.get('payment_terms', 'N/A')}</td></tr>
                    </table>
                </div>
            </div>
            """
        },
        "new_po": {
            "subject": f"📦 New Purchase Order: PO #{data.get('po_number', 'N/A')} - ₹{data.get('total_amount', 0):,.2f}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%); padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">New Purchase Order Created</h2>
                </div>
                <div style="padding: 25px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;"><strong>A new purchase order has been created:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">PO Number:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: #0891b2;">{data.get('po_number', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Order ID:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{data.get('order_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">RFQ Title:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('rfq_title', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Buyer:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('buyer_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Vendor:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('vendor_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Amount:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; font-size: 18px; color: #0891b2;">₹{data.get('total_amount', 0):,.2f}</td></tr>
                        <tr><td style="padding: 8px; color: #64748b;">Status:</td><td style="padding: 8px;">{data.get('status', 'N/A')}</td></tr>
                    </table>
                </div>
            </div>
            """
        },
        "new_dispute": {
            "subject": f"⚠️ New Dispute Filed: {data.get('subject', 'Dispute')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); padding: 20px; text-align: center;">
                    <h2 style="color: white; margin: 0;">⚠️ New Dispute Filed</h2>
                </div>
                <div style="padding: 25px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;"><strong>A dispute requires your attention:</strong></p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Dispute ID:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{data.get('dispute_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Order ID:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{data.get('order_id', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Type:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: #dc2626;">{data.get('dispute_type', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Subject:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">{data.get('subject', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Initiated By:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('initiated_by', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Buyer:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('buyer_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Vendor:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{data.get('vendor_name', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Order Amount:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">₹{data.get('order_amount', 0):,.2f}</td></tr>
                        <tr><td style="padding: 8px; color: #64748b;">Filed At:</td><td style="padding: 8px;">{data.get('created_at', 'N/A')}</td></tr>
                    </table>
                    <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 12px; margin-top: 15px;">
                        <p style="margin: 0; color: #991b1b; font-weight: bold;">Action Required: Please review this dispute in the admin dashboard.</p>
                    </div>
                </div>
            </div>
            """
        }
    }
    
    template = templates.get(event_type)
    if not template:
        logger.warning(f"Unknown admin notification type: {event_type}")
        return None
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"[OEMLinker Admin] {template['subject']}",
            "html": template["html"]
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Admin notification sent for {event_type}: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to send admin notification for {event_type}: {str(e)}")
        return None

def get_email_template(template_type: str, data: dict) -> tuple:
    """Get email subject and HTML content for various notification types"""
    
    templates = {
        "vendor_matched": {
            "subject": f"🎯 New RFQ Match ({data.get('match_score', 0)}%): {data.get('rfq_title', 'New Opportunity')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">New RFQ Match!</h1>
                    <p style="color: rgba(255,255,255,0.9); margin-top: 10px; font-size: 18px;">Match Score: {data.get('match_score', 0)}%</p>
                </div>
                <div style="padding: 30px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;">Hello {data.get('vendor_name', 'Vendor')},</p>
                    <p style="font-size: 16px; color: #334155;">Great news! You've been matched to a new RFQ based on your machine capabilities.</p>
                    
                    <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #f97316;">
                        <h3 style="color: #1e293b; margin-top: 0;">{data.get('rfq_title', 'RFQ')}</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td style="color: #64748b; padding: 8px 0;"><strong>Material:</strong></td><td style="color: #1e293b;">{data.get('material', 'N/A')}</td></tr>
                            <tr><td style="color: #64748b; padding: 8px 0;"><strong>Quantity:</strong></td><td style="color: #1e293b;">{data.get('quantity', 'N/A')} units</td></tr>
                            <tr><td style="color: #64748b; padding: 8px 0;"><strong>Tolerance:</strong></td><td style="color: #1e293b;">±{data.get('tolerance', 'N/A')}mm</td></tr>
                            <tr><td style="color: #64748b; padding: 8px 0;"><strong>Buyer:</strong></td><td style="color: #1e293b;">{data.get('buyer_name', 'N/A')}</td></tr>
                        </table>
                    </div>
                    
                    <div style="background: #ecfdf5; border-radius: 8px; padding: 15px; margin: 20px 0;">
                        <p style="color: #059669; margin: 0; font-weight: bold;">✓ Why You Matched:</p>
                        <p style="color: #064e3b; margin: 8px 0 0 0; font-size: 14px;">
                            <strong>Machines:</strong> {data.get('matching_machines', 'Compatible equipment')}<br/>
                            <strong>Capabilities:</strong> {data.get('process_matches', 'Matching processes')}
                        </p>
                    </div>
                    
                    <p style="font-size: 16px; color: #334155;">Log in to OEMLinker to view full details and submit your quote.</p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{data.get('app_url', '#')}" style="background: #f97316; color: white; padding: 14px 35px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">View RFQ & Submit Quote</a>
                    </div>
                </div>
                <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p>OEMLinker - AI-Powered Manufacturing Marketplace</p>
                    <p>You received this because your match score is 50% or higher.</p>
                </div>
            </div>
            """
        },
        "quote_received": {
            "subject": f"New Quote Received for {data.get('rfq_title', 'Your RFQ')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">New Quote Received!</h1>
                </div>
                <div style="padding: 30px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;">Hello {data.get('buyer_name', 'Buyer')},</p>
                    <p style="font-size: 16px; color: #334155;">A vendor has submitted a quote for your RFQ.</p>
                    
                    <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #22c55e;">
                        <h3 style="color: #1e293b; margin-top: 0;">{data.get('rfq_title', 'RFQ')}</h3>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Vendor:</strong> {data.get('vendor_name', 'N/A')}</p>
                        <p style="color: #22c55e; font-size: 24px; margin: 15px 0;"><strong>${data.get('price', '0.00')}</strong></p>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Lead Time:</strong> {data.get('lead_time', 'N/A')} days</p>
                    </div>
                    
                    <p style="font-size: 16px; color: #334155;">Log in to review and compare quotes.</p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{data.get('app_url', '#')}" style="background: #f97316; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Quotes</a>
                    </div>
                </div>
                <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p>OEMLinker - AI-Powered Manufacturing Marketplace</p>
                </div>
            </div>
            """
        },
        "quote_accepted": {
            "subject": f"Congratulations! Your Quote Was Accepted",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Quote Accepted!</h1>
                </div>
                <div style="padding: 30px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;">Hello {data.get('vendor_name', 'Vendor')},</p>
                    <p style="font-size: 16px; color: #334155;">Great news! Your quote has been accepted.</p>
                    
                    <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #22c55e;">
                        <h3 style="color: #1e293b; margin-top: 0;">{data.get('rfq_title', 'RFQ')}</h3>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Buyer:</strong> {data.get('buyer_name', 'N/A')}</p>
                        <p style="color: #22c55e; font-size: 24px; margin: 15px 0;"><strong>${data.get('price', '0.00')}</strong></p>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Order ID:</strong> {data.get('order_id', 'N/A')}</p>
                    </div>
                    
                    <p style="font-size: 16px; color: #334155;">Please log in to view the purchase order details and begin production.</p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{data.get('app_url', '#')}" style="background: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Order</a>
                    </div>
                </div>
                <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p>OEMLinker - AI-Powered Manufacturing Marketplace</p>
                </div>
            </div>
            """
        },
        "order_status_update": {
            "subject": f"Order Update: {data.get('order_id', 'Your Order')} - {data.get('status', 'Updated')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Order Update</h1>
                </div>
                <div style="padding: 30px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;">Hello {data.get('recipient_name', 'User')},</p>
                    <p style="font-size: 16px; color: #334155;">Your order status has been updated.</p>
                    
                    <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #3b82f6;">
                        <h3 style="color: #1e293b; margin-top: 0;">Order #{data.get('order_id', 'N/A')}</h3>
                        <p style="color: #64748b; margin: 5px 0;"><strong>RFQ:</strong> {data.get('rfq_title', 'N/A')}</p>
                        <p style="color: #3b82f6; font-size: 18px; margin: 15px 0;"><strong>Status: {data.get('status', 'N/A').replace('_', ' ').title()}</strong></p>
                        {f"<p style='color: #64748b; margin: 5px 0;'><strong>Note:</strong> {data.get('note', '')}</p>" if data.get('note') else ''}
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{data.get('app_url', '#')}" style="background: #3b82f6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Order</a>
                    </div>
                </div>
                <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p>OEMLinker - AI-Powered Manufacturing Marketplace</p>
                </div>
            </div>
            """
        },
        "new_message": {
            "subject": f"New Message from {data.get('sender_name', 'Someone')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">New Message</h1>
                </div>
                <div style="padding: 30px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;">Hello {data.get('recipient_name', 'User')},</p>
                    <p style="font-size: 16px; color: #334155;">You have a new message on OEMLinker.</p>
                    
                    <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #8b5cf6;">
                        <p style="color: #64748b; margin: 0 0 10px 0;"><strong>From:</strong> {data.get('sender_name', 'N/A')}</p>
                        <p style="color: #1e293b; font-style: italic;">"{data.get('message_preview', '')[:200]}..."</p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{data.get('app_url', '#')}" style="background: #8b5cf6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Message</a>
                    </div>
                </div>
                <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p>OEMLinker - AI-Powered Manufacturing Marketplace</p>
                </div>
            </div>
            """
        }
    }
    
    template = templates.get(template_type, {})
    return template.get("subject", "OEMLinker Notification"), template.get("html", "<p>Notification</p>")

# ============== MODELS ==============

class UserRole:
    BUYER = "buyer"
    VENDOR = "vendor"
    ADMIN = "admin"

# Helper function to check if user has admin-level access
# This includes users with admin role OR users with custom_role (staff users)
def has_admin_access(user: dict) -> bool:
    """Check if user has admin-level access (admin role or custom_role)"""
    return user.get("role") == UserRole.ADMIN or user.get("custom_role") is not None

class UserBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    name: str
    role: str = UserRole.BUYER

class UserCreate(UserBase):
    password: str
    # Optional vendor-specific fields
    gstin: Optional[str] = None
    company_name: Optional[str] = None
    trade_name: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        # Additional email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower().strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        v = sanitize_input(v)
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Name must be less than 100 characters')
        return v

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    role: str
    custom_role: Optional[str] = None
    picture: Optional[str] = None
    company_name: Optional[str] = None
    email_verified: bool = False
    phone_login: bool = False  # True if user registered via WhatsApp
    contact_email: Optional[str] = None  # Email for notifications (for WhatsApp users)
    created_at: str

class LoginRequest(BaseModel):
    email: str  # Can be email or phone number
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class VendorProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    vendor_id: str
    user_id: str
    company_name: str
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    description: Optional[str] = None
    gstin: Optional[str] = None
    gst_verified: bool = False
    gst_status: Optional[str] = None
    taxpayer_type: Optional[str] = None
    constitution: Optional[str] = None
    gst_registration_date: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    certifications: List[str] = []
    industries: List[str] = []
    materials_handled: List[str] = []
    past_experiences: List[dict] = []  # List of {title, description, industry, material, year}
    is_approved: bool = False
    rating: float = 0.0
    total_jobs: int = 0
    created_at: str

class PastExperience(BaseModel):
    """Vendor's past project experience for matching"""
    title: str
    description: Optional[str] = None
    industry: Optional[str] = None
    material: Optional[str] = None
    processes_used: List[str] = []
    part_type: Optional[str] = None  # e.g., "shaft", "housing", "bracket"
    year: Optional[int] = None

class VendorProfileCreate(BaseModel):
    company_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    certifications: List[str] = []
    industries: List[str] = []
    materials_handled: List[str] = []
    past_experiences: List[PastExperience] = []

class Machine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    machine_id: str
    vendor_id: str
    name: Optional[str] = None
    machine_category: Optional[str] = None
    machine_type: str
    brand: str
    model: str
    # Machine images
    images: List[str] = []  # List of image URLs
    # Standard dimensions
    max_x: Optional[float] = None
    max_y: Optional[float] = None
    max_z: Optional[float] = None
    max_diameter: Optional[float] = None
    max_length: Optional[float] = None
    max_swing: Optional[float] = None
    # Boring/Drilling specific
    bore_diameter: Optional[float] = None
    outer_diameter: Optional[float] = None
    spindle_bore: Optional[float] = None
    spindle_travel: Optional[float] = None
    arm_length: Optional[float] = None
    max_depth: Optional[float] = None
    # VTL/Table specific
    table_diameter: Optional[float] = None
    table_size_x: Optional[float] = None
    table_size_y: Optional[float] = None
    pallet_size: Optional[float] = None
    max_weight: Optional[float] = None
    # Shaping specific
    max_stroke: Optional[float] = None
    stroke: Optional[float] = None
    # Gear specific
    max_module: Optional[float] = None
    min_teeth: Optional[int] = None
    # 5-Axis specific
    a_axis_range: Optional[float] = None
    c_axis_range: Optional[float] = None
    # Sheet Metal/Press specific
    tonnage: Optional[float] = None
    max_thickness: Optional[float] = None
    # Laser specific
    laser_power: Optional[float] = None
    # Welding specific
    amperage: Optional[float] = None
    # Heat Treatment specific
    max_temp: Optional[float] = None
    # Inspection specific
    accuracy: Optional[float] = None
    # Additive specific
    layer_thickness: Optional[float] = None
    # EDM specific
    max_taper_angle: Optional[float] = None
    # Common fields
    tolerance_capability: float = 0.1
    tolerance: Optional[float] = None
    axis_config: Optional[str] = None
    materials_supported: List[str] = []
    materials: Optional[List[str]] = None
    monthly_capacity_hours: int = 160
    is_active: bool = True
    # Availability status
    availability_status: str = "available"  # available, engaged, maintenance, offline
    engaged_until: Optional[str] = None  # ISO date when machine becomes available
    engaged_order_id: Optional[str] = None  # Order ID the machine is engaged with
    availability_note: Optional[str] = None  # Optional note about availability
    created_at: str

class MachineCreate(BaseModel):
    name: Optional[str] = None
    machine_category: Optional[str] = None
    machine_type: str
    brand: str
    model: str
    # Machine images
    images: List[str] = []  # List of image URLs
    # Standard dimensions
    max_x: Optional[float] = None
    max_y: Optional[float] = None
    max_z: Optional[float] = None
    max_diameter: Optional[float] = None
    max_length: Optional[float] = None
    max_swing: Optional[float] = None
    # Boring/Drilling specific
    bore_diameter: Optional[float] = None
    outer_diameter: Optional[float] = None
    spindle_bore: Optional[float] = None
    spindle_travel: Optional[float] = None
    arm_length: Optional[float] = None
    max_depth: Optional[float] = None
    # VTL/Table specific
    table_diameter: Optional[float] = None
    table_size_x: Optional[float] = None
    table_size_y: Optional[float] = None
    pallet_size: Optional[float] = None
    max_weight: Optional[float] = None
    # Shaping specific
    max_stroke: Optional[float] = None
    stroke: Optional[float] = None
    # Gear specific
    max_module: Optional[float] = None
    min_teeth: Optional[int] = None
    # 5-Axis specific
    a_axis_range: Optional[float] = None
    c_axis_range: Optional[float] = None
    # Sheet Metal/Press specific
    tonnage: Optional[float] = None
    max_thickness: Optional[float] = None
    # Laser specific
    laser_power: Optional[float] = None
    # Welding specific
    amperage: Optional[float] = None
    # Heat Treatment specific
    max_temp: Optional[float] = None
    # Inspection specific
    accuracy: Optional[float] = None
    # Additive specific
    layer_thickness: Optional[float] = None
    # EDM specific
    max_taper_angle: Optional[float] = None
    # Common fields
    tolerance_capability: float = 0.1
    tolerance: Optional[float] = None
    axis_config: Optional[str] = None
    materials_supported: List[str] = []
    materials: Optional[List[str]] = None
    monthly_capacity_hours: int = 160
    # Availability status
    availability_status: str = "available"  # available, engaged, maintenance, offline
    engaged_until: Optional[str] = None
    availability_note: Optional[str] = None

class RFQStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ANALYZING = "analyzing"
    MATCHING = "matching"
    QUOTED = "quoted"
    PO_ISSUED = "po_issued"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class SupplyType:
    VENDOR_MATERIAL = "vendor_material"  # Vendor supplies material
    BUYER_MATERIAL = "buyer_material"    # Buyer supplies material (service only)

class RFQ(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rfq_id: str
    buyer_id: str
    title: str
    description: Optional[str] = None
    material_type: str
    quantity: int
    tolerance: float  # mm
    surface_finish: Optional[str] = None
    supply_type: str = SupplyType.VENDOR_MATERIAL
    deadline: Optional[str] = None
    urgency: str = "normal"  # urgent, high, normal, low
    status: str = RFQStatus.DRAFT
    drawing_ids: List[str] = []
    ai_analysis: Optional[Dict[str, Any]] = None
    matched_vendors: List[Dict[str, Any]] = []
    preferred_payment_terms: Optional[str] = None  # Buyer's preferred payment terms
    payment_terms_notes: Optional[str] = None  # Additional payment terms notes
    created_at: str
    updated_at: str

# Urgency levels
class UrgencyLevel:
    URGENT = "urgent"      # Immediate need, deadline < 3 days
    HIGH = "high"          # High priority, deadline 3-7 days
    NORMAL = "normal"      # Standard, deadline > 7 days
    LOW = "low"            # No rush, flexible timeline

URGENCY_LABELS = {
    "urgent": "🔴 Urgent",
    "high": "🟠 High Priority", 
    "normal": "🟢 Normal",
    "low": "🔵 Low Priority"
}

# Machine Categories Definition (used for AI identification and forms)
MACHINE_CATEGORIES = {
    "CNC Turning/Lathe": {
        "types": ["CNC Lathe", "CNC Turning", "Swiss Lathe", "CNC Turn-Mill"],
    },
    "VTL (Vertical Turret Lathe)": {
        "types": ["VTL", "Vertical Turret Lathe", "CNC VTL", "Double Column VTL"],
    },
    "VMC (Vertical Machining Center)": {
        "types": ["VMC", "CNC VMC", "High Speed VMC", "Heavy Duty VMC", "Double Column VMC"],
    },
    "HMC (Horizontal Machining Center)": {
        "types": ["HMC", "CNC HMC", "Pallet HMC", "High Speed HMC"],
    },
    "5-Axis Machining": {
        "types": ["5-Axis VMC", "5-Axis HMC", "5-Axis Mill-Turn", "5-Axis Gantry"],
    },
    "Milling": {
        "types": ["CNC Milling", "Vertical Milling", "Horizontal Milling", "Bed Type Milling", "Gantry Milling"],
    },
    "Boring": {
        "types": ["Horizontal Boring", "Jig Boring", "Fine Boring", "CNC Boring"],
    },
    "Grinding": {
        "types": ["Surface Grinding", "Cylindrical Grinding", "Centerless Grinding", "Internal Grinding", "Tool & Cutter Grinding"],
    },
    "Wire EDM": {
        "types": ["Wire EDM", "CNC Wire Cut", "Slow Wire EDM", "Fast Wire EDM"],
    },
    "Die Sinking EDM": {
        "types": ["Die Sinking EDM", "CNC EDM", "Mirror EDM"],
    },
    "Drilling": {
        "types": ["Radial Drilling", "CNC Drilling", "Deep Hole Drilling", "Multi-Spindle Drilling", "Gang Drilling"],
    },
    "Casting": {
        "types": ["Sand Casting", "Investment Casting", "Die Casting", "Gravity Die Casting", "Pressure Die Casting", "Centrifugal Casting", "Shell Moulding", "Lost Wax Casting", "Continuous Casting"],
    },
    "Forging": {
        "types": ["Open Die Forging", "Closed Die Forging", "Drop Forging", "Press Forging", "Roll Forging", "Upset Forging", "Ring Rolling", "Cold Forging", "Hot Forging"],
    },
    "Sheet Metal": {
        "types": ["Laser Cutting", "Plasma Cutting", "Waterjet Cutting", "CNC Turret Punch", "Press Brake", "Shearing Machine", "Rolling Machine"],
    },
    "Welding": {
        "types": ["MIG Welding", "TIG Welding", "Spot Welding", "Robotic Welding", "Laser Welding", "Electron Beam Welding"],
    },
    "Heat Treatment": {
        "types": ["Furnace", "Induction Hardening", "Case Hardening", "Annealing", "Quenching", "Tempering"],
    },
    "Surface Treatment": {
        "types": ["Shot Blasting", "Sand Blasting", "Electroplating", "Anodizing", "Powder Coating", "Painting"],
    },
    "Inspection/CMM": {
        "types": ["CMM", "Vision System", "Profile Projector", "Roughness Tester", "Hardness Tester", "3D Scanner"],
    },
    "Additive Manufacturing": {
        "types": ["FDM", "SLA", "SLS", "DMLS", "SLM", "Binder Jetting", "Metal 3D Printing"],
    }
}

# Payment Terms Options
class PaymentTerms:
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    ADVANCE_50_DELIVERY_50 = "50_advance_50_delivery"
    ADVANCE_100 = "100_advance"
    AGAINST_DELIVERY = "against_delivery"
    MILESTONE_BASED = "milestone_based"
    LETTER_OF_CREDIT = "letter_of_credit"
    CUSTOM = "custom"

PAYMENT_TERMS_LABELS = {
    "net_30": "Net 30 Days",
    "net_45": "Net 45 Days",
    "net_60": "Net 60 Days",
    "50_advance_50_delivery": "50% Advance, 50% on Delivery",
    "100_advance": "100% Advance",
    "against_delivery": "Payment Against Delivery",
    "milestone_based": "Milestone-Based Payment",
    "letter_of_credit": "Letter of Credit (LC)",
    "custom": "Custom Terms"
}

# Incoterms options
class Incoterms:
    EXW = "EXW"  # Ex Works
    FCA = "FCA"  # Free Carrier
    FAS = "FAS"  # Free Alongside Ship
    FOB = "FOB"  # Free on Board
    CFR = "CFR"  # Cost and Freight
    CIF = "CIF"  # Cost, Insurance and Freight
    CPT = "CPT"  # Carriage Paid To
    CIP = "CIP"  # Carriage and Insurance Paid To
    DAP = "DAP"  # Delivered at Place
    DPU = "DPU"  # Delivered at Place Unloaded
    DDP = "DDP"  # Delivered Duty Paid

INCOTERMS_LABELS = {
    "EXW": "EXW - Ex Works",
    "FCA": "FCA - Free Carrier",
    "FAS": "FAS - Free Alongside Ship",
    "FOB": "FOB - Free on Board",
    "CFR": "CFR - Cost and Freight",
    "CIF": "CIF - Cost, Insurance and Freight",
    "CPT": "CPT - Carriage Paid To",
    "CIP": "CIP - Carriage and Insurance Paid To",
    "DAP": "DAP - Delivered at Place",
    "DPU": "DPU - Delivered at Place Unloaded",
    "DDP": "DDP - Delivered Duty Paid"
}

class RFQCreate(BaseModel):
    title: str
    description: Optional[str] = None
    material_type: str
    quantity: int = 1
    tolerance: float = 0.1
    surface_finish: Optional[str] = None
    supply_type: str = SupplyType.VENDOR_MATERIAL
    deadline: Optional[str] = None
    urgency: str = "normal"  # urgent, high, normal, low
    preferred_payment_terms: Optional[str] = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None
    # New fields for delivery and vendor preferences
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_country: Optional[str] = None
    delivery_pincode: Optional[str] = None
    incoterms: Optional[str] = Incoterms.EXW
    preferred_vendor_countries: Optional[List[str]] = None  # List of preferred countries
    preferred_vendor_cities: Optional[List[str]] = None  # List of preferred cities

class Drawing(BaseModel):
    model_config = ConfigDict(extra="ignore")
    drawing_id: str
    rfq_id: str
    filename: str
    file_type: str
    file_size: int
    file_data: str  # Base64 encoded
    ai_analysis: Optional[Dict[str, Any]] = None
    created_at: str

class Quote(BaseModel):
    model_config = ConfigDict(extra="ignore")
    quote_id: str
    rfq_id: str
    vendor_id: str
    price: float  # Legacy: total price (backward compatibility)
    currency: str = "INR"
    lead_time_days: int
    notes: Optional[str] = None
    proposed_payment_terms: Optional[str] = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None
    is_selected: bool = False
    status: str = "pending"  # pending, accepted, rejected, expired
    # Enhanced quotation fields
    material_provided_by_buyer: bool = False  # If true, buyer provides raw material (legacy, for single-item RFQs)
    material_cost: Optional[float] = None  # Cost of raw material (if vendor provides)
    machining_cost: float = 0  # Cost of machining/labor
    additional_costs: Optional[Dict[str, float]] = None  # Heat treatment, finishing, etc.
    total_cost: float = 0  # Auto-calculated: material + machining + additional
    cost_breakdown_remarks: Optional[str] = None  # Detailed breakdown explanation
    # Item-wise quotation fields
    is_itemwise: bool = False  # True if quote has item-wise breakdown
    items: Optional[List[Dict[str, Any]]] = None  # Item-wise quotation details
    created_at: str
    expires_at: str

class QuoteCreate(BaseModel):
    rfq_id: str
    price: float = 0  # Legacy field, will be auto-calculated
    currency: str = "INR"
    lead_time_days: int
    notes: Optional[str] = None
    proposed_payment_terms: Optional[str] = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None
    # Enhanced quotation fields
    material_provided_by_buyer: bool = False
    material_cost: Optional[float] = None
    machining_cost: float = 0
    additional_costs: Optional[Dict[str, float]] = None  # e.g., {"heat_treatment": 500, "surface_finish": 200}
    cost_breakdown_remarks: Optional[str] = None

# Quotation Item for per-drawing quotation
class QuotationItem(BaseModel):
    item_id: str  # References RFQ item / drawing
    drawing_id: Optional[str] = None
    title: Optional[str] = None
    material_provided_by_buyer: bool = False
    material_cost: float = 0  # Cost of raw material (if vendor provides)
    labour_cost: float = 0  # Machining / labor cost
    additional_costs: Optional[Dict[str, float]] = None  # {"heat_treatment": 500, "finishing": 200}
    total_cost: float = 0  # Auto-calculated
    remarks: Optional[str] = None

# Item-wise Quotation Request
class ItemwiseQuotationCreate(BaseModel):
    rfq_id: str
    currency: str = "INR"
    lead_time_days: int
    notes: Optional[str] = None
    proposed_payment_terms: Optional[str] = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None
    items: List[QuotationItem]  # Per-item quotation details

# RFQ Item for Multi-Drawing RFQs
class RFQItem(BaseModel):
    item_id: str
    drawing_id: Optional[str] = None
    drawing_url: Optional[str] = None
    filename: Optional[str] = None
    title: str
    material_type: Optional[str] = None
    quantity: int = 1
    specifications: Optional[str] = None
    tolerance: Optional[float] = None
    process_detected: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None

# RFQ Line Item for Multi-Drawing RFQs (keeping for backward compatibility)
class RFQLineItem(BaseModel):
    line_item_id: str
    rfq_id: str  # Parent RFQ
    drawing_id: str
    title: str
    quantity: int = 1
    process_detected: Optional[str] = None  # machining, casting, forging, fabrication
    raw_material_provided: bool = False
    material_type: Optional[str] = None
    tolerance: Optional[float] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    matched_vendors: List[str] = []  # Vendor IDs matched for this line item
    status: str = "pending"  # pending, analyzing, matched, quoted

# AI Analysis Result
class AIAnalysisResult(BaseModel):
    process_detected: str  # machining, casting, forging, fabrication, multi
    processes_required: List[str] = []  # All processes needed
    raw_material_provided: bool = False
    material_type: Optional[str] = None
    tolerance: Optional[float] = None
    complexity_score: int = 5  # 1-10
    recommended_machine_categories: List[str] = []
    notes: Optional[str] = None

# Vendor Match Result
class VendorMatchResult(BaseModel):
    vendor_id: str
    company_name: str
    suitability_score: int  # 0-100
    matched_capabilities: List[str] = []
    match_reason: str
    is_excluded: bool = False
    exclusion_reason: Optional[str] = None

# Notification Types
class NotificationType:
    RFQ_MATCHED = "rfq_matched"
    QUOTE_RECEIVED = "quote_received"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    ORDER_CREATED = "order_created"
    ORDER_STATUS_UPDATE = "order_status_update"
    PAYMENT_RECEIVED = "payment_received"
    MESSAGE_RECEIVED = "message_received"

class OrderStatus:
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    IN_PRODUCTION = "in_production"
    QUALITY_CHECK = "quality_check"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    order_id: str
    rfq_id: str
    quote_id: str
    buyer_id: str
    vendor_id: str
    total_amount: float
    currency: str = "INR"
    status: str = OrderStatus.PENDING_PAYMENT
    payment_status: str = "pending"
    payment_terms: Optional[str] = None  # Finalized payment terms
    payment_terms_notes: Optional[str] = None
    po_number: Optional[str] = None  # Purchase Order number
    tracking_updates: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str

class RatingCreate(BaseModel):
    overall_rating: float  # 1-5
    quality_rating: float  # 1-5
    communication_rating: float  # 1-5
    delivery_rating: float  # 1-5
    review_text: Optional[str] = None
    would_recommend: bool = True

# ============== AUTH HELPERS ==============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    # Check cookie first
    token = request.cookies.get("session_token")
    
    # Then check Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Try session token from Emergent Auth first
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        expires_at = session.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        
        user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
        if user:
            return user
    
    # Try JWT token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_optional(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

# ============== NOTIFICATION HELPER ==============

async def create_notification(
    user_id: str, 
    notification_type: str, 
    title: str, 
    message: str, 
    data: dict = None,
    send_email: bool = False,
    email_template: str = None,
    email_data: dict = None
):
    """Create an in-app notification and optionally send email"""
    now = datetime.now(timezone.utc).isoformat()
    
    notification = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "is_read": False,
        "created_at": now
    }
    
    await db.notifications.insert_one(notification)
    
    # Send email if requested
    if send_email and email_template and email_data:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1})
        if user and user.get("email"):
            subject, html = get_email_template(email_template, email_data)
            asyncio.create_task(send_email_async(user["email"], subject, html))
    
    return notification

# ============== AUTH ROUTES ==============

async def send_verification_email(email: str, name: str, verification_token: str):
    """Send email verification link to new user"""
    # Use frontend URL for the verification link
    frontend_url = os.environ.get("FRONTEND_URL", "https://oemlinker.com")
    verification_link = f"{frontend_url}/verify-email?token={verification_token}"
    
    email_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Welcome to OEMLinker!</h1>
        </div>
        <div style="padding: 30px; background: #f8fafc;">
            <p style="font-size: 16px; color: #334155;">Hello {name},</p>
            <p style="font-size: 16px; color: #334155;">Thank you for registering with OEMLinker - the AI-Powered Manufacturing Marketplace.</p>
            <p style="font-size: 16px; color: #334155;">Please verify your email address to activate your account and start connecting with manufacturers.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_link}" style="background: #f97316; color: white; padding: 14px 35px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Verify Email Address</a>
            </div>
            
            <p style="font-size: 14px; color: #64748b;">This verification link will expire in 24 hours.</p>
            <p style="font-size: 14px; color: #64748b;">If you didn't create an account, please ignore this email.</p>
            
            <div style="background: #fff; border-radius: 8px; padding: 15px; margin-top: 20px; border-left: 4px solid #f97316;">
                <p style="margin: 0; font-size: 12px; color: #64748b;">
                    <strong>Can't click the button?</strong> Copy and paste this link into your browser:<br/>
                    <span style="color: #3b82f6; word-break: break-all;">{verification_link}</span>
                </p>
            </div>
        </div>
        <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
            <p>OEMLinker - Connecting OEMs with Trusted Vendors</p>
        </div>
    </div>
    '''
    
    await send_email_async(email, "Verify Your OEMLinker Account", email_html)

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate, request: Request):
    # Get client IP for rate limiting
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
    
    # Record this registration attempt
    record_registration_attempt(client_ip)
    
    # Sanitize and normalize email
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
    
    # Log successful registration
    logger.info(f"New user registered: {email} (ID: {user_id}) from IP: {client_ip}")
    
    # Send admin notification for new user
    asyncio.create_task(send_admin_notification("new_user", {
        "name": name,
        "email": email,
        "role": user_data.role,
        "company_name": user_data.company_name if user_data.role == "vendor" else "N/A",
        "created_at": now
    }))
    
    # If vendor role with company details, create vendor profile
    vendor_company_name = None
    if user_data.role == "vendor" and user_data.company_name:
        vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
        vendor_doc = {
            "vendor_id": vendor_id,
            "user_id": user_id,
            "company_name": user_data.company_name,
            "trade_name": user_data.trade_name or "",
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
        
        # Update user document with company name
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
            custom_role=None,
            picture=None,
            company_name=vendor_company_name,
            email_verified=False,
            phone_login=False,
            contact_email=None,
            created_at=user_doc["created_at"]
        )
    )

# ============== EMAIL VERIFICATION ENDPOINTS ==============

class EmailVerificationRequest(BaseModel):
    token: str

@api_router.post("/auth/verify-email")
async def verify_email(verification_data: EmailVerificationRequest):
    """Verify user's email address using token from email"""
    token_hash = hash_token(verification_data.token)
    
    # Find user with this verification token
    user = await db.users.find_one({"verification_token_hash": token_hash}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    
    # Check if already verified
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
    
    # Mark email as verified
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {"email_verified": True},
            "$unset": {"verification_token_hash": "", "verification_expires": ""}
        }
    )
    
    logger.info(f"Email verified for user: {user['email']}")
    
    return {"message": "Email verified successfully", "email": user["email"]}

@api_router.post("/auth/resend-verification")
async def resend_verification_email(user: dict = Depends(get_current_user)):
    """Resend verification email to current user"""
    if user.get("email_verified"):
        return {"message": "Email already verified"}
    
    # Generate new verification token
    verification_token = generate_secure_token(32)
    verification_token_hash = hash_token(verification_token)
    verification_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    
    # Update user with new token
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {
                "verification_token_hash": verification_token_hash,
                "verification_expires": verification_expires
            }
        }
    )
    
    # Send verification email
    asyncio.create_task(send_verification_email(user["email"], user["name"], verification_token))
    
    logger.info(f"Verification email resent to: {user['email']}")
    
    return {"message": "Verification email sent. Please check your inbox."}

# ============== ADMIN SETUP (ONE-TIME USE) ==============
class AdminSetup(BaseModel):
    email: str
    password: str
    name: str
    setup_key: str

@api_router.post("/admin/setup")
async def setup_admin(setup_data: AdminSetup):
    """
    One-time admin setup endpoint. 
    Requires ADMIN_SETUP_KEY environment variable to be set.
    Creates an admin user if no admin exists.
    """
    # Check setup key
    expected_key = os.environ.get("ADMIN_SETUP_KEY", "OEMLinker2024SecureSetup!")
    if setup_data.setup_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid setup key")
    
    # Check if admin already exists
    existing_admin = await db.users.find_one({"role": "admin"})
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin already exists. Use login instead.")
    
    # Check if email already taken
    existing_email = await db.users.find_one({"email": setup_data.email.lower()})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create admin user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    admin_doc = {
        "user_id": user_id,
        "email": setup_data.email.lower().strip(),
        "password_hash": hash_password(setup_data.password),
        "name": setup_data.name,
        "role": "admin",
        "is_verified": True,
        "created_at": now,
        "updated_at": now
    }
    
    await db.users.insert_one(admin_doc)
    logger.info(f"Admin user created: {setup_data.email}")
    
    token = create_jwt_token(user_id, setup_data.email, "admin")
    
    return {
        "message": "Admin account created successfully",
        "access_token": token,
        "user": {
            "user_id": user_id,
            "email": setup_data.email,
            "name": setup_data.name,
            "role": "admin"
        }
    }

@api_router.post("/auth/login")
async def login(login_data: LoginRequest, request: Request):
    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Sanitize input - can be email or phone number
    login_id = sanitize_input(login_data.email.lower().strip())
    
    # Normalize phone number if it looks like one (all digits, possibly with +)
    normalized_phone = login_id.replace("+", "").replace(" ", "").replace("-", "")
    is_phone_login = normalized_phone.isdigit() and len(normalized_phone) >= 10
    
    # Check if account is locked
    if is_account_locked(login_id):
        remaining = get_lockout_remaining(login_id)
        logger.warning(f"Login attempt on locked account: {login_id} from IP: {client_ip}")
        raise HTTPException(
            status_code=423, 
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {remaining // 60} minutes."
        )
    
    # Find user - try email first, then phone number
    user = await db.users.find_one({"email": login_id}, {"_id": 0})
    
    # If not found by email field, also try contact_email (for users who added email later)
    if not user and "@" in login_id:
        user = await db.users.find_one({"contact_email": login_id}, {"_id": 0})
    
    # If not found by email and looks like phone, try phone number variations
    if not user and is_phone_login:
        # Get last 10 digits for lookup
        phone_10digit = normalized_phone[-10:] if len(normalized_phone) >= 10 else normalized_phone
        
        # Try finding by 10-digit phone (primary method for WhatsApp users)
        user = await db.users.find_one({"email": phone_10digit}, {"_id": 0})
        
        # Also try with 91 prefix for backward compatibility
        if not user:
            user = await db.users.find_one({"email": f"91{phone_10digit}"}, {"_id": 0})
        
        # Try full normalized number as fallback
        if not user and normalized_phone != phone_10digit:
            user = await db.users.find_one({"email": normalized_phone}, {"_id": 0})
        
        # For WhatsApp users who updated their email, check the 'phone' field
        if not user:
            # Try finding by phone field with various formats (WhatsApp users)
            user = await db.users.find_one({
                "phone": {"$in": [phone_10digit, f"91{phone_10digit}", f"+91{phone_10digit}", normalized_phone]},
                "phone_login": True
            }, {"_id": 0})
        
        # For any user with phone field (web-registered users who added phone)
        if not user:
            user = await db.users.find_one({
                "phone": {"$in": [phone_10digit, f"91{phone_10digit}", f"+91{phone_10digit}", normalized_phone]}
            }, {"_id": 0})
        
        # For web-registered users, check vendor profile phone field
        if not user:
            # Find vendor by phone number
            vendor = await db.vendors.find_one({
                "phone": {"$in": [phone_10digit, f"91{phone_10digit}", f"+91{phone_10digit}", normalized_phone, f"+91 {phone_10digit[:5]} {phone_10digit[5:]}"]}
            }, {"_id": 0, "user_id": 1})
            
            if vendor:
                # Get the associated user
                user = await db.users.find_one({"user_id": vendor["user_id"]}, {"_id": 0})
    
    if not user:
        # Record failed attempt (use login_id even if not found to prevent enumeration)
        record_login_attempt(login_id, False)
        logger.warning(f"Failed login attempt for non-existent user: {login_id} from IP: {client_ip}")
        # Use same error message to prevent user enumeration
        raise HTTPException(status_code=401, detail="Invalid email/phone or password")
    
    # Verify password
    if not verify_password(login_data.password, user.get("password_hash", "")):
        record_login_attempt(login_id, False)
        
        # Update failed attempts in DB
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$inc": {"failed_login_attempts": 1}}
        )
        
        logger.warning(f"Failed login attempt for: {login_id} from IP: {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid email/phone or password")
    
    # Check if 2FA is enabled
    security_settings = user.get("security_settings", {})
    two_factor_enabled = security_settings.get("two_factor_enabled", False)
    user_email = user.get("email", "")
    
    if two_factor_enabled and "@" in user_email:
        # Generate and send OTP (only for email users)
        otp = generate_otp()
        store_otp(user_email, otp)
        
        # Send OTP email
        otp_html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1e40af;">🔐 Your Login Verification Code</h2>
            <p>Hello {user.get("name", "User")},</p>
            <p>Your one-time verification code is:</p>
            <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin: 20px 0; text-align: center;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1e40af;">{otp}</span>
            </div>
            <p style="color: #666;">This code expires in {OTP_EXPIRY_MINUTES} minutes.</p>
            <p style="color: #dc2626; font-size: 14px;"><strong>If you didn't request this code, please ignore this email and secure your account.</strong></p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">OEMLinker - AI-Powered Manufacturing Marketplace</p>
        </div>
        '''
        asyncio.create_task(send_email_async(user_email, "🔐 Your OEMLinker Login Code", otp_html))
        
        logger.info(f"2FA OTP sent to: {user_email} from IP: {client_ip}")
        
        return {
            "requires_2fa": True,
            "message": "Verification code sent to your email",
            "email_hint": f"{user_email[:3]}***{user_email[user_email.index('@'):]}"
        }
    
    # No 2FA - proceed with normal login
    record_login_attempt(login_id, True)
    
    # Update user login info
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {
                "last_login": datetime.now(timezone.utc).isoformat(),
                "last_login_ip": client_ip,
                "failed_login_attempts": 0
            },
            "$inc": {"login_count": 1}
        }
    )
    
    logger.info(f"Successful login: {login_id} from IP: {client_ip}")
    
    token = create_jwt_token(user["user_id"], user["email"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            custom_role=user.get("custom_role"),
            picture=user.get("picture"),
            company_name=user.get("company_name"),
            email_verified=user.get("email_verified", False),
            phone_login=user.get("phone_login", False),
            contact_email=user.get("contact_email"),
            created_at=user.get("created_at", datetime.now(timezone.utc).isoformat())
        )
    )

# ============== 2FA ENDPOINTS ==============

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str
    password: str  # Re-verify password for security

@api_router.post("/auth/verify-otp")
async def verify_otp_endpoint(otp_data: OTPVerifyRequest, request: Request):
    """Verify OTP and complete login"""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    email = sanitize_input(otp_data.email.lower().strip())
    
    # Find user and verify password again
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(otp_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify OTP
    success, message = verify_otp(email, otp_data.otp)
    if not success:
        logger.warning(f"Failed OTP verification for: {email} from IP: {client_ip} - {message}")
        raise HTTPException(status_code=400, detail=message)
    
    # OTP verified - complete login
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
            custom_role=user.get("custom_role"),
            picture=user.get("picture"),
            company_name=user.get("company_name"),
            email_verified=user.get("email_verified", False),
            phone_login=user.get("phone_login", False),
            contact_email=user.get("contact_email"),
            created_at=user["created_at"]
        )
    )

@api_router.post("/auth/resend-otp")
async def resend_otp(request: Request):
    """Resend OTP for 2FA"""
    body = await request.json()
    email = sanitize_input(body.get("email", "").lower().strip())
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        # Don't reveal if user exists
        return {"message": "If an account exists, a new code has been sent."}
    
    # Generate and send new OTP
    otp = generate_otp()
    store_otp(email, otp)
    
    otp_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1e40af;">🔐 Your New Login Verification Code</h2>
        <p>Hello {user.get("name", "User")},</p>
        <p>Your new one-time verification code is:</p>
        <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin: 20px 0; text-align: center;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1e40af;">{otp}</span>
        </div>
        <p style="color: #666;">This code expires in {OTP_EXPIRY_MINUTES} minutes.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">OEMLinker - AI-Powered Manufacturing Marketplace</p>
    </div>
    '''
    asyncio.create_task(send_email_async(email, "🔐 Your New OEMLinker Login Code", otp_html))
    
    return {"message": "A new verification code has been sent to your email."}

class TwoFactorToggle(BaseModel):
    enable: bool
    password: str  # Require password to change 2FA settings

@api_router.post("/auth/2fa/toggle")
async def toggle_2fa(
    toggle_data: TwoFactorToggle, 
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Enable or disable 2FA for the user"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Verify password
    db_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not db_user or not verify_password(toggle_data.password, db_user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Invalid password")
    
    # Update 2FA setting
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"security_settings.two_factor_enabled": toggle_data.enable}}
    )
    
    action = "enabled" if toggle_data.enable else "disabled"
    
    # Send notification email
    alert_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: {'#f0fdf4' if toggle_data.enable else '#fef2f2'}; border-left: 4px solid {'#22c55e' if toggle_data.enable else '#ef4444'}; padding: 16px; margin-bottom: 20px;">
            <h2 style="color: {'#166534' if toggle_data.enable else '#dc2626'}; margin: 0 0 8px 0;">🔐 Two-Factor Authentication {action.capitalize()}</h2>
        </div>
        <p>Hello {db_user.get("name", "User")},</p>
        <p>Two-factor authentication has been <strong>{action}</strong> for your OEMLinker account.</p>
        {'<p style="color: #166534;">Your account is now more secure. You will receive a verification code via email each time you log in.</p>' if toggle_data.enable else '<p style="color: #dc2626;"><strong>Warning:</strong> Your account is now less secure. Consider re-enabling 2FA for better protection.</p>'}
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">OEMLinker - AI-Powered Manufacturing Marketplace</p>
    </div>
    '''
    asyncio.create_task(send_email_async(user["email"], f"🔐 2FA {action.capitalize()} - Security Update", alert_html))
    
    logger.info(f"2FA {action} for user: {user['email']} from IP: {client_ip}")
    
    return {"message": f"Two-factor authentication has been {action}", "two_factor_enabled": toggle_data.enable}

@api_router.get("/auth/2fa/status")
async def get_2fa_status(user: dict = Depends(get_current_user)):
    """Get current 2FA status for the user"""
    db_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    security_settings = db_user.get("security_settings", {}) if db_user else {}
    
    return {
        "two_factor_enabled": security_settings.get("two_factor_enabled", False),
        "password_changed_at": security_settings.get("password_changed_at")
    }

@api_router.post("/auth/session")
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
    
    # Check if user exists
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user:
        user_id = user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "role": UserRole.BUYER,  # Default role
            "picture": picture,
            "password_hash": None,
            "company_name": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)
    
    # Store session
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
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

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "custom_role": user.get("custom_role"),
        "picture": user.get("picture"),
        "company_name": user.get("company_name"),
        "email_verified": user.get("email_verified", False),
        "phone_login": user.get("phone_login", False),
        "contact_email": user.get("contact_email"),
        "created_at": user["created_at"]
    }

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}

# ============== MAGIC LINK (WhatsApp Auto-Login) ==============

# Magic link tokens are stored in MongoDB for persistence across instances

async def generate_magic_link_for_user(user_id: str, redirect_url: str = None) -> dict:
    """
    Generate a magic link token for any user (buyer, vendor, or admin).
    Used for WhatsApp notifications to enable instant login.
    
    Args:
        user_id: User's unique ID
        redirect_url: Path to redirect to after login (e.g., /buyer/rfq/rfq_123)
    
    Returns:
        dict with success, token, and redirect_url
    """
    try:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            logger.warning(f"Magic link generation failed: User not found for user_id {user_id}")
            return {"success": False, "error": "User not found"}
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)  # 30 min expiry
        
        # Validate and sanitize redirect URL - only allow internal paths
        safe_redirect = None
        if redirect_url:
            # Only allow relative paths starting with /
            if redirect_url.startswith("/") and not redirect_url.startswith("//"):
                # Whitelist of allowed redirect patterns
                allowed_patterns = ["/vendor/", "/buyer/", "/admin/", "/dashboard", "/rfq/", "/quotes", "/orders"]
                if any(pattern in redirect_url for pattern in allowed_patterns):
                    safe_redirect = redirect_url
        
        # Store token in MongoDB with redirect URL
        await db.magic_link_tokens.insert_one({
            "token": token,
            "user_id": user["user_id"],
            "redirect_url": safe_redirect,
            "expires_at": expires_at.isoformat(),
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "whatsapp_notification"
        })
        
        logger.info(f"Magic link generated for user {user_id} with redirect to {safe_redirect}")
        
        return {
            "success": True,
            "token": token,
            "expires_in_minutes": 30,
            "redirect_url": safe_redirect
        }
    except Exception as e:
        logger.error(f"Magic link generation error: {str(e)}")
        return {"success": False, "error": str(e)}

@api_router.post("/auth/magic-link/generate")
async def generate_magic_link(phone: str, redirect_url: Optional[str] = None):
    """Generate a magic link token for WhatsApp users (internal use only)
    
    Args:
        phone: User's phone number
        redirect_url: Optional URL to redirect to after successful login (e.g., /vendor/rfq/rfq_123)
    """
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


@api_router.get("/auth/magic-link/verify/{token}")
async def verify_magic_link(token: str, response: Response):
    """Verify magic link token and create session"""
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

# ============== PASSWORD SECURITY ENDPOINTS ==============

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v

@api_router.post("/auth/change-password")
async def change_password(
    password_data: PasswordChangeRequest, 
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Change password for authenticated user"""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Verify current password
    db_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(password_data.current_password, db_user.get("password_hash", "")):
        logger.warning(f"Failed password change attempt for user: {user['email']}")
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Check new password is different
    if password_data.current_password == password_data.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")
    
    # Update password
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
    
    # Send security alert email
    alert_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 16px; margin-bottom: 20px;">
            <h2 style="color: #dc2626; margin: 0 0 8px 0;">🔐 Security Alert</h2>
            <p style="color: #7f1d1d; margin: 0;">Your password was changed</p>
        </div>
        <p>Hello {db_user.get("name", "User")},</p>
        <p>Your OEMLinker account password was successfully changed.</p>
        <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px 0;"><strong>Time:</strong> {now.strftime("%B %d, %Y at %I:%M %p UTC")}</p>
            <p style="margin: 0;"><strong>IP Address:</strong> {client_ip}</p>
        </div>
        <p style="color: #dc2626; font-weight: bold;">If you did not make this change, please:</p>
        <ol style="color: #666;">
            <li>Reset your password immediately</li>
            <li>Contact our support team</li>
            <li>Review your account activity</li>
        </ol>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">OEMLinker - AI-Powered Manufacturing Marketplace</p>
    </div>
    '''
    asyncio.create_task(send_email_async(user["email"], "🔐 Password Changed - Security Alert", alert_html))
    
    logger.info(f"Password changed successfully for user: {user['email']} from IP: {client_ip}")
    return {"message": "Password changed successfully"}

@api_router.post("/auth/forgot-password")
async def forgot_password(reset_request: PasswordResetRequest, request: Request):
    """Request password reset email"""
    client_ip = request.client.host if request.client else "unknown"
    email = sanitize_input(reset_request.email.lower().strip())
    
    # Always return success to prevent email enumeration
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user:
        # Generate secure reset token
        reset_token = generate_secure_token(32)
        token_hash = hash_token(reset_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Store reset token in DB
        await db.password_resets.delete_many({"email": email})  # Remove old tokens
        await db.password_resets.insert_one({
            "email": email,
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "used": False
        })
        
        # Send reset email - always use production URL
        reset_link = f"https://oemlinker.com/reset-password?token={reset_token}"
        
        email_html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1e40af;">Password Reset Request</h2>
            <p>Hello {user.get("name", "User")},</p>
            <p>We received a request to reset your password for your OEMLinker account.</p>
            <p>Click the button below to reset your password. This link will expire in 1 hour.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #f97316; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Reset Password</a>
            </div>
            <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email or contact support if you have concerns.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">OEMLinker - AI-Powered Manufacturing Marketplace</p>
        </div>
        '''
        
        asyncio.create_task(send_email_async(email, "Reset Your OEMLinker Password", email_html))
        logger.info(f"Password reset requested for: {email} from IP: {client_ip}")
    else:
        logger.warning(f"Password reset requested for non-existent email: {email} from IP: {client_ip}")
    
    # Always return success to prevent enumeration
    return {"message": "If an account exists with that email, you will receive a password reset link shortly."}

@api_router.post("/auth/reset-password")
async def reset_password(reset_data: PasswordResetConfirm, request: Request):
    """Reset password using token from email"""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    token_hash = hash_token(reset_data.token)
    
    # Find valid reset token
    reset_record = await db.password_resets.find_one({
        "token_hash": token_hash,
        "used": False
    }, {"_id": 0})
    
    if not reset_record:
        logger.warning(f"Invalid password reset token attempt from IP: {client_ip}")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check expiration
    expires_at = datetime.fromisoformat(reset_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        await db.password_resets.delete_one({"token_hash": token_hash})
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")
    
    email = reset_record["email"]
    
    # Get user for email
    db_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    # Update password
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
    
    # Mark token as used
    await db.password_resets.update_one(
        {"token_hash": token_hash},
        {"$set": {"used": True}}
    )
    
    # Remove from locked accounts if locked
    if email in locked_accounts:
        del locked_accounts[email]
    
    # Send security alert email
    user_name = db_user.get("name", "User") if db_user else "User"
    alert_html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 16px; margin-bottom: 20px;">
            <h2 style="color: #dc2626; margin: 0 0 8px 0;">🔐 Security Alert</h2>
            <p style="color: #7f1d1d; margin: 0;">Your password was reset</p>
        </div>
        <p>Hello {user_name},</p>
        <p>Your OEMLinker account password was successfully reset using the password recovery process.</p>
        <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px 0;"><strong>Time:</strong> {now.strftime("%B %d, %Y at %I:%M %p UTC")}</p>
            <p style="margin: 0;"><strong>IP Address:</strong> {client_ip}</p>
        </div>
        <p style="color: #dc2626; font-weight: bold;">If you did not request this password reset:</p>
        <ol style="color: #666;">
            <li>Your email account may be compromised</li>
            <li>Contact our support team immediately</li>
            <li>Secure your email account</li>
        </ol>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">OEMLinker - AI-Powered Manufacturing Marketplace</p>
    </div>
    '''
    asyncio.create_task(send_email_async(email, "🔐 Password Reset - Security Alert", alert_html))
    
    logger.info(f"Password reset successfully for: {email} from IP: {client_ip}")
    return {"message": "Password has been reset successfully. You can now log in with your new password."}

@api_router.put("/auth/role")
async def update_role(request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    new_role = body.get("role")
    
    if new_role not in [UserRole.BUYER, UserRole.VENDOR]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"role": new_role}}
    )
    
    return {"message": "Role updated", "role": new_role}

# ============== USER PROFILE ROUTES ==============

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    website: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None

@api_router.get("/user/profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    db_user = await db.users.find_one(
        {"user_id": user["user_id"]}, 
        {"_id": 0, "password_hash": 0}
    )
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@api_router.put("/user/profile")
async def update_user_profile(
    profile: UserProfileUpdate, 
    user: dict = Depends(get_current_user)
):
    """Update current user's profile"""
    update_data = {k: v for k, v in profile.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return updated user
    db_user = await db.users.find_one(
        {"user_id": user["user_id"]}, 
        {"_id": 0, "password_hash": 0}
    )
    return db_user

# ============== VENDOR ROUTES ==============

@api_router.post("/vendors/profile", response_model=VendorProfile)
async def create_vendor_profile(profile: VendorProfileCreate, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.VENDOR:
        raise HTTPException(status_code=403, detail="Only vendors can create profiles")
    
    existing = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Vendor profile already exists")
    
    vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
    vendor_doc = {
        "vendor_id": vendor_id,
        "user_id": user["user_id"],
        **profile.model_dump(),
        "is_approved": False,
        "rating": 0.0,
        "total_jobs": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.vendors.insert_one(vendor_doc)
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"company_name": profile.company_name}}
    )
    
    return VendorProfile(**vendor_doc)

@api_router.get("/vendors/profile")
async def get_vendor_profile(user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    return vendor

@api_router.put("/vendors/profile")
async def update_vendor_profile(profile: VendorProfileCreate, user: dict = Depends(get_current_user)):
    # Get the update data but EXCLUDE past_experiences to preserve them
    update_data = profile.model_dump()
    # Remove past_experiences from update to prevent overwriting
    # Past experiences are managed separately via /vendors/experiences endpoints
    update_data.pop("past_experiences", None)
    
    result = await db.vendors.update_one(
        {"user_id": user["user_id"]},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Sync company_name to user record
    # Note: contact_email is for notifications only
    # NEVER change the primary email field for phone_login users - it breaks their login
    user_update = {"company_name": profile.company_name}
    if profile.contact_email:
        # Always update contact_email for notifications (separate from login email)
        user_update["contact_email"] = profile.contact_email
        
        # Do NOT update primary email if user has phone_login flag
        # This preserves their phone number as login ID
        if not user.get("phone_login"):
            # Only for regular email users who don't have a login email yet
            current_email = user.get("email", "")
            if not current_email or current_email == "":
                user_update["email"] = profile.contact_email
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": user_update}
    )
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return vendor

@api_router.get("/vendors/list")
async def list_vendors(approved_only: bool = True):
    query = {"is_approved": True} if approved_only else {}
    vendors = await db.vendors.find(query, {"_id": 0}).to_list(100)
    return vendors

# ============== VENDOR PAST EXPERIENCE ==============
# NOTE: These routes MUST come BEFORE /vendors/{vendor_id} routes to avoid path conflicts

@api_router.post("/vendors/experiences")
async def add_past_experience(experience: PastExperience, user: dict = Depends(get_current_user)):
    """Add a past experience to vendor profile"""
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can add experiences")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        # Auto-create vendor profile if it doesn't exist
        logger.info(f"Creating vendor profile for user {user['user_id']}")
        vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        vendor = {
            "vendor_id": vendor_id,
            "user_id": user["user_id"],
            "company_name": user.get("name", ""),
            "is_approved": False,
            "past_experiences": [],
            "created_at": now,
            "updated_at": now
        }
        await db.vendors.insert_one(vendor)
    
    experience_doc = {
        "experience_id": f"exp_{uuid.uuid4().hex[:12]}",
        "title": experience.title,
        "description": experience.description or "",
        "industry": experience.industry or "",
        "material": experience.material or "",
        "processes_used": experience.processes_used or [],
        "part_type": experience.part_type or "",
        "year": experience.year,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.vendors.update_one(
        {"vendor_id": vendor["vendor_id"]},
        {"$push": {"past_experiences": experience_doc}}
    )
    
    logger.info(f"Experience added for vendor {vendor['vendor_id']}: {experience.title}, modified: {result.modified_count}")
    
    return {"message": "Experience added successfully", "experience": experience_doc}

@api_router.get("/vendors/experiences")
async def get_my_experiences(user: dict = Depends(get_current_user)):
    """Get vendor's past experiences"""
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can view their experiences")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0, "past_experiences": 1})
    if not vendor:
        # Return empty if no vendor profile yet
        return {"experiences": []}
    
    return {"experiences": vendor.get("past_experiences", [])}

@api_router.delete("/vendors/experiences/{experience_id}")
async def delete_experience(experience_id: str, user: dict = Depends(get_current_user)):
    """Delete a past experience"""
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can delete their experiences")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    result = await db.vendors.update_one(
        {"vendor_id": vendor["vendor_id"]},
        {"$pull": {"past_experiences": {"experience_id": experience_id}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Experience not found")
    
    return {"message": "Experience deleted successfully"}

@api_router.get("/vendors/{vendor_id}")
async def get_vendor_by_id(vendor_id: str):
    vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor

@api_router.get("/vendors/{vendor_id}/full")
async def get_vendor_full_profile(vendor_id: str, user: dict = Depends(get_current_user)):
    """Get full vendor profile including machines and stats"""
    vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get vendor's machines
    machines = await db.machines.find({"vendor_id": vendor_id, "is_active": True}, {"_id": 0}).to_list(50)
    
    # Get vendor's completed jobs count
    completed_orders = await db.orders.count_documents({"vendor_id": vendor_id, "status": "completed"})
    
    # Get vendor's quotes stats
    total_quotes = await db.quotes.count_documents({"vendor_id": vendor_id})
    accepted_quotes = await db.quotes.count_documents({"vendor_id": vendor_id, "status": "accepted"})
    
    # Get user contact info
    vendor_user = await db.users.find_one({"user_id": vendor["user_id"]}, {"_id": 0, "email": 1, "name": 1})
    
    return {
        **vendor,
        "machines": machines,
        "stats": {
            "completed_orders": completed_orders,
            "total_quotes": total_quotes,
            "accepted_quotes": accepted_quotes,
            "acceptance_rate": round((accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0, 1)
        },
        "contact": {
            "email": vendor_user.get("email") if vendor_user else None,
            "name": vendor_user.get("name") if vendor_user else None,
            "phone": vendor.get("phone"),
            "website": vendor.get("website")
        }
    }

# ============== GSTIN VERIFICATION ==============

# GSTIN API Key
GSTIN_API_KEY = os.environ.get("GSTIN_API_KEY", "6720148bc8d7ed819c0e757afae0be70")

@api_router.get("/gstin/verify/{gstin}")
async def verify_gstin(gstin: str):
    """Verify GSTIN and fetch company details from GST database"""
    import httpx
    
    # Validate GSTIN format (15 characters)
    gstin = gstin.upper().strip()
    if len(gstin) != 15:
        raise HTTPException(status_code=400, detail="Invalid GSTIN format. GSTIN must be 15 characters.")
    
    # GSTIN format: 2 digit state code + 10 digit PAN + 1 digit entity number + 1 Z + 1 checksum
    gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    import re
    if not re.match(gstin_pattern, gstin):
        raise HTTPException(status_code=400, detail="Invalid GSTIN format")
    
    # State codes mapping
    state_codes = {
        "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
        "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
        "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
        "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
        "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
        "24": "Gujarat", "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
        "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
        "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman & Nicobar",
        "36": "Telangana", "37": "Andhra Pradesh (New)", "38": "Ladakh"
    }
    
    state_code = gstin[:2]
    state = state_codes.get(state_code, "Unknown")
    
    # Extract PAN from GSTIN (characters 3-12)
    pan = gstin[2:12]
    
    try:
        # Try primary API - gstincheck.co.in with API key
        async with httpx.AsyncClient(timeout=15.0) as client:
            api_url = f"http://sheet.gstincheck.co.in/check/{GSTIN_API_KEY}/{gstin}"
            logger.info(f"Verifying GSTIN: {gstin}")
            response = await client.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("flag"):
                    # API returned valid data
                    gst_data = data.get("data", {})
                    
                    # Extract address components
                    principal_place = gst_data.get("pradr", {}).get("addr", {})
                    address_parts = []
                    if principal_place.get("bno"):
                        address_parts.append(principal_place.get("bno"))
                    if principal_place.get("flno"):
                        address_parts.append(principal_place.get("flno"))
                    if principal_place.get("bnm"):
                        address_parts.append(principal_place.get("bnm"))
                    if principal_place.get("st"):
                        address_parts.append(principal_place.get("st"))
                    if principal_place.get("loc"):
                        address_parts.append(principal_place.get("loc"))
                    if principal_place.get("dst"):
                        address_parts.append(principal_place.get("dst"))
                    
                    return {
                        "valid": True,
                        "gstin": gstin,
                        "legal_name": gst_data.get("lgnm", ""),
                        "trade_name": gst_data.get("tradeNam", ""),
                        "status": gst_data.get("sts", ""),
                        "taxpayer_type": gst_data.get("dty", ""),
                        "state": principal_place.get("stcd") or state,
                        "city": principal_place.get("dst", ""),
                        "pincode": principal_place.get("pncd", ""),
                        "address": ", ".join(filter(None, address_parts)),
                        "constitution": gst_data.get("ctb", ""),
                        "registration_date": gst_data.get("rgdt", ""),
                        "last_updated": gst_data.get("lstupdt", "")
                    }
                else:
                    # Check error code
                    error_code = data.get("errorCode", "")
                    error_message = data.get("message", "GSTIN verification failed")
                    
                    # If API key issue or GST server issue, return partial data from GSTIN structure
                    if error_code in ["API_KEY_INVALID", "API_KEY_EXPIRED", "NO_BALANCE", "GST_SERVER_UNDER_MAINTENANCE"]:
                        logger.warning(f"GSTIN API issue: {error_code}")
                        # Return basic info extracted from GSTIN format
                        return {
                            "valid": True,
                            "gstin": gstin,
                            "legal_name": "",
                            "trade_name": "",
                            "status": "Verification Pending",
                            "taxpayer_type": "",
                            "state": state,
                            "city": "",
                            "pincode": "",
                            "address": "",
                            "constitution": "",
                            "registration_date": "",
                            "last_updated": "",
                            "pan": pan,
                            "note": f"GSTIN format valid. Manual verification recommended. ({error_message})"
                        }
                    
                    # GSTIN not found in database
                    return {
                        "valid": False,
                        "gstin": gstin,
                        "error": error_message,
                        "state": state,
                        "pan": pan
                    }
            else:
                logger.warning(f"GSTIN API error: {response.status_code}")
                
    except Exception as e:
        logger.error(f"GSTIN verification error: {str(e)}")
    
    # Fallback: Extract basic info from GSTIN structure
    entity_type_codes = {
        "P": "Individual/Proprietor", "F": "Firm/LLP", "C": "Company",
        "H": "HUF", "A": "AOP", "B": "BOI", "T": "Trust", "G": "Government",
        "L": "Local Authority", "J": "Artificial Juridical Person"
    }
    entity_type = entity_type_codes.get(pan[3], "Business")
    
    return {
        "valid": True,
        "gstin": gstin,
        "legal_name": "",
        "trade_name": "",
        "status": "Format Valid - Online verification unavailable",
        "taxpayer_type": entity_type,
        "state": state,
        "city": "",
        "pincode": "",
        "address": "",
        "constitution": entity_type,
        "registration_date": "",
        "last_updated": "",
        "pan": pan,
        "note": "GSTIN format is valid. Company details will be manually verified."
    }

# ============== LOCATION/CITIES ROUTES ==============

# Major manufacturing cities by country (India only)
MAJOR_CITIES_BY_COUNTRY = {
    "India": [
        "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Ahmedabad",
        "Kolkata", "Coimbatore", "Ludhiana", "Faridabad", "Gurgaon", "Noida",
        "Jamshedpur", "Indore", "Nashik", "Vadodara", "Rajkot", "Surat", "Haora",
        "Tiruchirappalli", "Salem", "Hosur", "Aurangabad", "Nagpur", "Visakhapatnam",
        "Madurai", "Thiruvananthapuram", "Kochi", "Bhopal", "Raipur", "Ranchi",
        "Lucknow", "Kanpur", "Agra", "Varanasi", "Patna", "Guwahati", "Chandigarh",
        "Jalandhar", "Amritsar", "Jodhpur", "Jaipur", "Udaipur", "Bhilai"
    ]
}

@api_router.get("/locations/cities")
async def get_cities_by_countries(countries: str = None):
    """
    Get cities for given countries with vendor presence highlighted.
    Returns hybrid list: vendor cities first, then major manufacturing cities.
    
    Query params:
    - countries: Comma-separated list of country names (e.g., "India,China")
    """
    result = {}
    
    # Parse countries from query string
    country_list = []
    if countries:
        country_list = [c.strip() for c in countries.split(",") if c.strip()]
    
    if not country_list:
        # Return all available countries with their cities
        country_list = list(MAJOR_CITIES_BY_COUNTRY.keys())
    
    for country in country_list:
        # Get vendors in this country
        vendors_in_country = await db.vendors.find(
            {"country": {"$regex": f"^{country}$", "$options": "i"}},
            {"_id": 0, "city": 1, "company_name": 1}
        ).to_list(100)
        
        # Extract unique vendor cities
        vendor_cities = {}
        for v in vendors_in_country:
            city = v.get("city", "").strip()
            if city:
                if city not in vendor_cities:
                    vendor_cities[city] = {"count": 0, "vendors": []}
                vendor_cities[city]["count"] += 1
                vendor_cities[city]["vendors"].append(v.get("company_name", "Unknown"))
        
        # Get major cities for this country
        major_cities = MAJOR_CITIES_BY_COUNTRY.get(country, [])
        
        # Build city list with vendor presence info
        cities = []
        added_cities = set()
        
        # First, add cities with vendors (highlighted)
        for city, info in sorted(vendor_cities.items(), key=lambda x: -x[1]["count"]):
            cities.append({
                "name": city,
                "has_vendors": True,
                "vendor_count": info["count"],
                "is_major": city in major_cities
            })
            added_cities.add(city.lower())
        
        # Then add major cities without vendors
        for city in major_cities:
            if city.lower() not in added_cities:
                cities.append({
                    "name": city,
                    "has_vendors": False,
                    "vendor_count": 0,
                    "is_major": True
                })
                added_cities.add(city.lower())
        
        result[country] = {
            "cities": cities,
            "vendor_city_count": len(vendor_cities),
            "total_cities": len(cities)
        }
    
    return result

@api_router.get("/locations/countries")
async def get_available_countries():
    """
    Get list of countries with vendor counts.
    """
    # Get unique countries from vendors
    pipeline = [
        {"$match": {"country": {"$exists": True, "$ne": ""}}},
        {"$group": {"_id": "$country", "vendor_count": {"$sum": 1}}},
        {"$sort": {"vendor_count": -1}}
    ]
    
    vendor_countries = await db.vendors.aggregate(pipeline).to_list(50)
    
    # Merge with predefined countries
    all_countries = set(MAJOR_CITIES_BY_COUNTRY.keys())
    for vc in vendor_countries:
        all_countries.add(vc["_id"])
    
    result = []
    for country in sorted(all_countries):
        vendor_info = next((vc for vc in vendor_countries if vc["_id"] == country), None)
        result.append({
            "name": country,
            "has_vendors": vendor_info is not None,
            "vendor_count": vendor_info["vendor_count"] if vendor_info else 0,
            "has_major_cities": country in MAJOR_CITIES_BY_COUNTRY
        })
    
    # Sort: countries with vendors first, then alphabetically
    result.sort(key=lambda x: (-x["vendor_count"], x["name"]))
    
    return {"countries": result}

# ============== CHAT/MESSAGING ROUTES ==============

class MessageCreate(BaseModel):
    receiver_id: str
    rfq_id: Optional[str] = None
    content: str

@api_router.post("/messages")
async def send_message(message: MessageCreate, user: dict = Depends(get_current_user)):
    """Send a message to another user"""
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Create conversation ID (sorted user IDs for consistency)
    participants = sorted([user["user_id"], message.receiver_id])
    conversation_id = f"conv_{participants[0]}_{participants[1]}"
    if message.rfq_id:
        conversation_id += f"_{message.rfq_id}"
    
    message_doc = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender_id": user["user_id"],
        "sender_name": user.get("name", "Unknown"),
        "sender_role": user.get("role", "buyer"),
        "receiver_id": message.receiver_id,
        "rfq_id": message.rfq_id,
        "content": message.content,
        "read": False,
        "created_at": now
    }
    
    await db.messages.insert_one(message_doc)
    
    # Update or create conversation
    await db.conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                "conversation_id": conversation_id,
                "participants": participants,
                "rfq_id": message.rfq_id,
                "last_message": message.content[:100],
                "last_message_at": now,
                "updated_at": now
            },
            "$setOnInsert": {
                "created_at": now
            }
        },
        upsert=True
    )
    
    # Create in-app notification for the receiver
    sender_name = user.get("name", "Someone")
    app_url = os.environ.get("APP_URL", "https://rfq-marketplace-9.preview.emergentagent.com")
    
    await create_notification(
        user_id=message.receiver_id,
        notification_type=NotificationType.MESSAGE_RECEIVED,
        title=f"New message from {sender_name}",
        message=message.content[:100] + ("..." if len(message.content) > 100 else ""),
        data={"conversation_id": conversation_id, "sender_id": user["user_id"], "rfq_id": message.rfq_id},
        send_email=True,
        email_template="new_message",
        email_data={
            "sender_name": sender_name,
            "recipient_name": "User",
            "message_preview": message.content,
            "app_url": f"{app_url}/chat/{conversation_id}"
        }
    )
    
    return {"message_id": message_id, "conversation_id": conversation_id}

@api_router.get("/messages/conversations")
async def get_conversations(user: dict = Depends(get_current_user)):
    """Get all conversations for current user"""
    conversations = await db.conversations.find(
        {"participants": user["user_id"]},
        {"_id": 0}
    ).sort("last_message_at", -1).to_list(50)
    
    # Enrich with other participant info
    for conv in conversations:
        other_user_id = [p for p in conv["participants"] if p != user["user_id"]][0]
        other_user = await db.users.find_one({"user_id": other_user_id}, {"_id": 0, "name": 1, "role": 1})
        
        # Get vendor info if vendor
        if other_user and other_user.get("role") == "vendor":
            vendor = await db.vendors.find_one({"user_id": other_user_id}, {"_id": 0, "company_name": 1})
            conv["other_party"] = {
                "user_id": other_user_id,
                "name": vendor.get("company_name") if vendor else other_user.get("name"),
                "role": "vendor"
            }
        else:
            conv["other_party"] = {
                "user_id": other_user_id,
                "name": other_user.get("name") if other_user else "Unknown",
                "role": other_user.get("role") if other_user else "buyer"
            }
        
        # Get unread count
        unread = await db.messages.count_documents({
            "conversation_id": conv["conversation_id"],
            "receiver_id": user["user_id"],
            "read": False
        })
        conv["unread_count"] = unread
        
        # Get RFQ title if linked
        if conv.get("rfq_id"):
            rfq = await db.rfqs.find_one({"rfq_id": conv["rfq_id"]}, {"_id": 0, "title": 1})
            conv["rfq_title"] = rfq.get("title") if rfq else None
    
    return conversations

@api_router.get("/messages/conversation/{conversation_id}")
async def get_conversation_messages(conversation_id: str, user: dict = Depends(get_current_user)):
    """Get messages in a conversation"""
    # Verify user is participant
    conv = await db.conversations.find_one(
        {"conversation_id": conversation_id, "participants": user["user_id"]},
        {"_id": 0}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    
    # Mark messages as read
    await db.messages.update_many(
        {"conversation_id": conversation_id, "receiver_id": user["user_id"], "read": False},
        {"$set": {"read": True}}
    )
    
    return {"conversation": conv, "messages": messages}

@api_router.get("/messages/with/{other_user_id}")
async def get_or_create_conversation(other_user_id: str, rfq_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Get or start a conversation with another user"""
    participants = sorted([user["user_id"], other_user_id])
    conversation_id = f"conv_{participants[0]}_{participants[1]}"
    if rfq_id:
        conversation_id += f"_{rfq_id}"
    
    conv = await db.conversations.find_one({"conversation_id": conversation_id}, {"_id": 0})
    
    if not conv:
        # Create new conversation
        now = datetime.now(timezone.utc).isoformat()
        conv = {
            "conversation_id": conversation_id,
            "participants": participants,
            "rfq_id": rfq_id,
            "last_message": None,
            "last_message_at": now,
            "created_at": now,
            "updated_at": now
        }
        await db.conversations.insert_one(conv)
        del conv["_id"]
    
    # Get other party info
    other_user = await db.users.find_one({"user_id": other_user_id}, {"_id": 0, "name": 1, "role": 1})
    if other_user and other_user.get("role") == "vendor":
        vendor = await db.vendors.find_one({"user_id": other_user_id}, {"_id": 0, "company_name": 1})
        conv["other_party"] = {
            "user_id": other_user_id,
            "name": vendor.get("company_name") if vendor else other_user.get("name"),
            "role": "vendor"
        }
    else:
        conv["other_party"] = {
            "user_id": other_user_id,
            "name": other_user.get("name") if other_user else "Unknown",
            "role": other_user.get("role") if other_user else "buyer"
        }
    
    # Get messages
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    
    return {"conversation": conv, "messages": messages}

@api_router.get("/messages/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    """Get total unread message count"""
    count = await db.messages.count_documents({
        "receiver_id": user["user_id"],
        "read": False
    })
    return {"unread_count": count}

# ============== MACHINE ROUTES ==============

@api_router.post("/machines", response_model=Machine)
async def add_machine(machine: MachineCreate, user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile required")
    
    machine_id = f"machine_{uuid.uuid4().hex[:12]}"
    machine_doc = {
        "machine_id": machine_id,
        "vendor_id": vendor["vendor_id"],
        **machine.model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.machines.insert_one(machine_doc)
    return Machine(**machine_doc)

@api_router.get("/machines")
async def list_my_machines(user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        return []
    
    machines = await db.machines.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).to_list(100)
    return machines

@api_router.get("/machines/{machine_id}")
async def get_machine(machine_id: str):
    machine = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return machine

@api_router.put("/machines/{machine_id}")
async def update_machine(machine_id: str, machine: MachineCreate, user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get existing machine to preserve images if not provided
    existing_machine = await db.machines.find_one(
        {"machine_id": machine_id, "vendor_id": vendor["vendor_id"]},
        {"_id": 0}
    )
    if not existing_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Build update data, preserving images if empty/not provided
    update_data = machine.model_dump()
    
    # Preserve existing images if new images list is empty
    if not update_data.get("images") and existing_machine.get("images"):
        update_data["images"] = existing_machine["images"]
    
    # Also preserve other fields that shouldn't be overwritten
    fields_to_preserve = ["ai_identified", "ai_confidence", "ai_description", "source", "created_at"]
    for field in fields_to_preserve:
        if field in existing_machine and field not in update_data:
            update_data[field] = existing_machine[field]
    
    result = await db.machines.update_one(
        {"machine_id": machine_id, "vendor_id": vendor["vendor_id"]},
        {"$set": update_data}
    )
    
    updated = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    return updated

@api_router.delete("/machines/{machine_id}")
async def delete_machine(machine_id: str, user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.machines.delete_one({"machine_id": machine_id, "vendor_id": vendor["vendor_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    return {"message": "Machine deleted"}

# Machine Image Upload
@api_router.post("/machines/{machine_id}/images")
async def upload_machine_image(
    machine_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload an image for a machine - stores in AWS S3"""
    from app.services.s3_storage_service import upload_file
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    machine = await db.machines.find_one(
        {"machine_id": machine_id, "vendor_id": vendor["vendor_id"]},
        {"_id": 0}
    )
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")
    
    # Read file content
    content = await file.read()
    
    # Check file size (max 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be less than 5MB")
    
    # Upload to AWS S3 (no local fallback - S3 is required)
    try:
        result = upload_file(
            data=content,
            filename=file.filename,
            folder=f"machines/{vendor['vendor_id']}",
            content_type=file.content_type
        )
        image_url = result["url"]  # Use S3 public URL
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to storage: {str(e)}")
    
    # Update machine with new image
    current_images = machine.get("images", [])
    current_images.append(image_url)
    
    await db.machines.update_one(
        {"machine_id": machine_id},
        {"$set": {"images": current_images}}
    )
    
    logger.info(f"Machine image uploaded to S3: {machine_id} - {image_url}")
    
    return {"image_url": image_url, "images": current_images}

@api_router.delete("/machines/{machine_id}/images")
async def delete_machine_image(
    machine_id: str,
    image_url: str,
    user: dict = Depends(get_current_user)
):
    """Delete an image from a machine"""
    from app.services.s3_storage_service import delete_file as s3_delete_file
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    machine = await db.machines.find_one(
        {"machine_id": machine_id, "vendor_id": vendor["vendor_id"]},
        {"_id": 0}
    )
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    current_images = machine.get("images", [])
    if image_url not in current_images:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Remove from list
    current_images.remove(image_url)
    
    await db.machines.update_one(
        {"machine_id": machine_id},
        {"$set": {"images": current_images}}
    )
    
    # Delete file from S3 if it's an S3 URL
    bucket_name = os.environ.get("AWS_S3_BUCKET_NAME", "oemlinker-storage")
    if f"{bucket_name}.s3." in image_url:
        # Extract S3 key from URL: https://bucket.s3.region.amazonaws.com/path/to/file.jpg
        try:
            s3_key = image_url.split(".amazonaws.com/")[1]
            s3_delete_file(s3_key)
            logger.info(f"Deleted S3 file: {s3_key}")
        except Exception as e:
            logger.warning(f"Failed to delete S3 file {image_url}: {e}")
    # Handle legacy local files
    elif image_url.startswith("/api/uploads/machines/"):
        filename = image_url.split("/")[-1]
        file_path = f"/app/uploads/machines/{filename}"
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted local file: {file_path}")
    
    return {"message": "Image deleted", "images": current_images}

# Serve uploaded machine images (legacy support for local files)
@api_router.get("/uploads/machines/{filename}")
async def serve_machine_image(filename: str):
    """Serve uploaded machine images - legacy endpoint for local files.
    New images are served directly from S3 URLs."""
    file_path = f"/app/uploads/machines/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found. Note: New images are stored in S3 and served directly via their S3 URL.")
    
    # Determine content type
    ext = filename.split(".")[-1].lower()
    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp"
    }
    content_type = content_types.get(ext, "image/jpeg")
    
    return FileResponse(file_path, media_type=content_type)


@api_router.get("/storage/{path:path}")
async def serve_cloud_storage_file(path: str):
    """Serve files from AWS S3 storage"""
    from app.services.s3_storage_service import download_file, AWS_S3_BUCKET_NAME
    
    # Strip bucket name prefix if incorrectly included in path
    # This handles old URLs like /api/storage/oemlinker/machines/...
    if path.startswith(f"{AWS_S3_BUCKET_NAME}/"):
        path = path[len(AWS_S3_BUCKET_NAME) + 1:]
    elif path.startswith("oemlinker-storage/"):
        path = path[len("oemlinker-storage/"):]
    elif path.startswith("oemlinker/"):
        path = path[len("oemlinker/"):]
    
    try:
        content, content_type = download_file(path)
        return Response(content=content, media_type=content_type)
    except Exception as e:
        logger.error(f"Failed to serve S3 file {path}: {e}")
        raise HTTPException(status_code=404, detail="File not found")


@api_router.get("/uploads/{path:path}")
async def serve_legacy_uploads(path: str):
    """
    Handle legacy /api/uploads/ URLs.
    These files were stored locally before S3 migration and no longer exist.
    Returns 404 with helpful message.
    """
    logger.warning(f"Legacy upload URL requested: /api/uploads/{path}")
    raise HTTPException(
        status_code=404, 
        detail="This file was stored in legacy format and is no longer available. Please re-upload the image."
    )


# ============== ADMIN FILE MANAGER ==============

@api_router.get("/admin/files")
async def list_storage_files(
    prefix: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List files in AWS S3 storage (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.s3_storage_service import list_files
    
    # Default to machines/drawings prefix
    search_prefix = prefix if prefix else ""
    result = list_files(search_prefix)
    
    return result


@api_router.delete("/admin/files/{path:path}")
async def delete_storage_file(
    path: str,
    user: dict = Depends(get_current_user)
):
    """Delete a file from AWS S3 storage (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.s3_storage_service import delete_file
    
    result = delete_file(path)
    
    if result.get("success"):
        return {"success": True, "message": f"File deleted: {path}"}
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Delete failed"))


@api_router.get("/admin/files/stats")
async def get_storage_stats(
    user: dict = Depends(get_current_user)
):
    """Get AWS S3 storage statistics (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.s3_storage_service import list_files
    
    # Get files by category
    machines_result = list_files("machines")
    drawings_result = list_files("drawings")
    
    machines_files = machines_result.get("files", [])
    drawings_files = drawings_result.get("files", [])
    
    total_size = sum(f.get("size", 0) for f in machines_files + drawings_files)
    
    return {
        "total_files": len(machines_files) + len(drawings_files),
        "machine_images": len(machines_files),
        "drawings": len(drawings_files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "storage": "AWS S3",
        "bucket": os.environ.get("AWS_S3_BUCKET_NAME", "oemlinker-storage")
    }


@api_router.post("/admin/migrate-image-urls")
async def migrate_image_urls(user: dict = Depends(get_current_user)):
    """
    Migrate old image URLs to S3 presigned URLs.
    Removes invalid /api/uploads/ URLs and converts S3 public URLs to presigned URLs.
    """
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.s3_storage_service import get_presigned_url, get_s3_client
    
    bucket_name = os.environ.get("AWS_S3_BUCKET_NAME", "oemlinker-storage")
    region = os.environ.get("AWS_REGION", "ap-south-1")
    s3_base = f"https://{bucket_name}.s3.{region}.amazonaws.com/"
    s3_base_alt = f"https://{bucket_name}.s3."
    
    stats = {
        "machines_updated": 0,
        "images_removed": 0,
        "images_migrated": 0,
        "vendors_updated": 0,
        "rfqs_updated": 0,
        "errors": []
    }
    
    def extract_s3_key(url: str) -> str:
        """Extract S3 key from various URL formats"""
        # Handle /api/storage/ URLs (with potential bucket name prefix)
        if url.startswith("/api/storage/"):
            key = url.replace("/api/storage/", "")
            # Strip bucket name prefix if present
            if key.startswith(f"{bucket_name}/"):
                key = key[len(bucket_name)+1:]
            elif key.startswith("oemlinker/"):
                key = key[len("oemlinker/"):]
            elif key.startswith("oemlinker-storage/"):
                key = key[len("oemlinker-storage/"):]
            return key if key else None
        elif s3_base in url:
            return url.split(s3_base)[-1].split("?")[0]  # Remove query params
        elif s3_base_alt in url and ".amazonaws.com/" in url:
            # Handle BUCKET.s3.REGION.amazonaws.com/KEY format
            return url.split(".amazonaws.com/")[-1].split("?")[0]
        elif f"s3.{region}.amazonaws.com/{bucket_name}/" in url:
            # Handle s3.REGION.amazonaws.com/BUCKET/KEY format (regional endpoint)
            return url.split(f"s3.{region}.amazonaws.com/{bucket_name}/")[-1].split("?")[0]
        elif "s3.amazonaws.com" in url:
            # Handle various S3 URL formats
            parts = url.split("amazonaws.com/")[-1].split("?")[0]
            # Remove bucket name if present at start
            if parts.startswith(f"{bucket_name}/"):
                return parts[len(bucket_name)+1:]
            return parts
        elif "emergent" in url and "/api/storage/" in url:
            key = url.split("/api/storage/")[-1].split("?")[0]
            # Strip bucket name prefix if present
            if key.startswith(f"{bucket_name}/"):
                key = key[len(bucket_name)+1:]
            elif key.startswith("oemlinker/"):
                key = key[len("oemlinker/"):]
            return key if key else None
        return None
    
    def generate_presigned(s3_key: str) -> str:
        """Generate a 7-day presigned URL (max allowed by S3)"""
        try:
            return get_presigned_url(s3_key, expiration=604800)  # 7 days (max)
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            return None
    
    # 1. Fix machine images
    machines = await db.machines.find({"images": {"$exists": True, "$ne": []}}).to_list(1000)
    for machine in machines:
        old_images = machine.get("images", [])
        new_images = []
        updated = False
        
        for img_url in old_images:
            # Force regeneration of all presigned URLs to ensure correct regional endpoint
            # Extract S3 key and generate presigned URL
            s3_key = extract_s3_key(img_url)
            if s3_key:
                presigned = generate_presigned(s3_key)
                if presigned:
                    new_images.append(presigned)
                    if presigned != img_url:
                        stats["images_migrated"] += 1
                        updated = True
                else:
                    stats["images_removed"] += 1
                    updated = True
            elif img_url.startswith("/api/uploads/"):
                # Remove old invalid uploads
                stats["images_removed"] += 1
                updated = True
            else:
                # Keep unknown URLs
                new_images.append(img_url)
        
        if updated or new_images != old_images:
            await db.machines.update_one(
                {"machine_id": machine["machine_id"]},
                {"$set": {"images": new_images}}
            )
            stats["machines_updated"] += 1
    
    # 2. Fix vendor profile images/logos
    vendors = await db.vendors.find({
        "$or": [
            {"logo_url": {"$exists": True, "$ne": None}},
            {"profile_image": {"$exists": True, "$ne": None}}
        ]
    }).to_list(500)
    
    for vendor in vendors:
        updates = {}
        for field in ["logo_url", "profile_image"]:
            url = vendor.get(field)
            if url:
                s3_key = extract_s3_key(url)
                if s3_key:
                    presigned = generate_presigned(s3_key)
                    if presigned:
                        updates[field] = presigned
                        stats["images_migrated"] += 1
                elif url.startswith("/api/uploads/"):
                    updates[field] = None
                    stats["images_removed"] += 1
        
        if updates:
            await db.vendors.update_one(
                {"vendor_id": vendor["vendor_id"]},
                {"$set": updates}
            )
            stats["vendors_updated"] += 1
    
    # 3. Fix RFQ drawing URLs
    rfqs = await db.rfqs.find({"drawings": {"$exists": True, "$ne": []}}).to_list(1000)
    for rfq in rfqs:
        drawings = rfq.get("drawings", [])
        updated = False
        
        for drawing in drawings:
            for url_field in ["url", "file_url", "s3_url", "preview_url"]:
                url = drawing.get(url_field)
                if url:
                    s3_key = extract_s3_key(url)
                    if s3_key:
                        presigned = generate_presigned(s3_key)
                        if presigned:
                            drawing[url_field] = presigned
                            stats["images_migrated"] += 1
                            updated = True
        
        if updated:
            await db.rfqs.update_one(
                {"rfq_id": rfq["rfq_id"]},
                {"$set": {"drawings": drawings}}
            )
            stats["rfqs_updated"] += 1
    
    logger.info(f"Image URL migration completed: {stats}")
    return {
        "success": True,
        "message": "Image URL migration completed - all images now use presigned URLs",
        "stats": stats
    }


# Machine Availability Update
class MachineAvailabilityUpdate(BaseModel):
    availability_status: str  # available, engaged, maintenance, offline
    engaged_until: Optional[str] = None  # ISO date
    availability_note: Optional[str] = None

@api_router.put("/machines/{machine_id}/availability")
async def update_machine_availability(
    machine_id: str, 
    availability: MachineAvailabilityUpdate, 
    user: dict = Depends(get_current_user)
):
    """Update machine availability status"""
    if user["role"] != UserRole.VENDOR:
        raise HTTPException(status_code=403, detail="Only vendors can update machine availability")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Validate status
    valid_statuses = ["available", "engaged", "maintenance", "offline"]
    if availability.availability_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    # Update machine
    update_data = {
        "availability_status": availability.availability_status,
        "availability_note": availability.availability_note
    }
    
    if availability.availability_status == "engaged" and availability.engaged_until:
        update_data["engaged_until"] = availability.engaged_until
    elif availability.availability_status == "available":
        update_data["engaged_until"] = None
        update_data["engaged_order_id"] = None
    
    result = await db.machines.update_one(
        {"machine_id": machine_id, "vendor_id": vendor["vendor_id"]},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    updated = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    return updated

@api_router.get("/machines/availability/summary")
async def get_machines_availability_summary(user: dict = Depends(get_current_user)):
    """Get summary of all machines availability for a vendor"""
    if user["role"] != UserRole.VENDOR:
        raise HTTPException(status_code=403, detail="Only vendors can view machine availability")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    machines = await db.machines.find(
        {"vendor_id": vendor["vendor_id"]},
        {"_id": 0, "machine_id": 1, "name": 1, "machine_type": 1, "brand": 1, "model": 1,
         "availability_status": 1, "engaged_until": 1, "availability_note": 1}
    ).to_list(100)
    
    # Count by status
    summary = {
        "available": 0,
        "engaged": 0,
        "maintenance": 0,
        "offline": 0,
        "total": len(machines)
    }
    
    for m in machines:
        status = m.get("availability_status", "available")
        if status in summary:
            summary[status] += 1
    
    return {
        "summary": summary,
        "machines": machines
    }

# ============== BULK MACHINE IMPORT ==============

import csv
from io import StringIO

class BulkImportResult(BaseModel):
    total_rows: int
    successful: int
    failed: int
    machines_created: List[dict]
    errors: List[dict]

@api_router.get("/machines/bulk-import/template")
async def get_bulk_import_template():
    """Get CSV template for bulk machine import"""
    template_content = """name,machine_category,machine_type,brand,model,max_x,max_y,max_z,max_diameter,max_length,max_swing,tolerance,materials_supported,monthly_capacity_hours
CNC Lathe 1,CNC Turning/Lathe,CNC Lathe,Mazak,Quick Turn 200,,,200,300,500,250,0.01,"Aluminum,Steel,Stainless Steel",160
VMC Machine 1,VMC (Vertical Machining Center),VMC,Haas,VF-2,762,406,508,,,,0.02,"Steel,Aluminum",200
5-Axis Mill,5-Axis Machining,5-Axis VMC,DMG Mori,DMU 50,500,450,400,300,,,0.005,"Titanium,Inconel,Steel",120"""
    
    return {
        "template": template_content,
        "instructions": {
            "name": "Machine name/identifier (optional, will auto-generate if empty)",
            "machine_category": "Category from: CNC Turning/Lathe, VMC (Vertical Machining Center), HMC (Horizontal Machining Center), 5-Axis Machining, VTL (Vertical Turret Lathe), Boring Machine, Grinding, EDM, Laser Cutting, Sheet Metal/Press, Welding, etc.",
            "machine_type": "Specific type within category (e.g., CNC Lathe, VMC, Wire EDM)",
            "brand": "Machine manufacturer (required)",
            "model": "Machine model number (required)",
            "max_x": "X-axis travel in mm (for milling/machining centers)",
            "max_y": "Y-axis travel in mm (for milling/machining centers)",
            "max_z": "Z-axis travel in mm",
            "max_diameter": "Maximum diameter in mm (for turning/boring)",
            "max_length": "Maximum length in mm",
            "max_swing": "Swing over bed in mm (for lathes)",
            "tolerance": "Achievable tolerance in mm (default: 0.01)",
            "materials_supported": "Comma-separated list of materials (e.g., Aluminum,Steel,Titanium)",
            "monthly_capacity_hours": "Available hours per month (default: 160)"
        },
        "valid_categories": [
            "CNC Turning/Lathe", "VMC (Vertical Machining Center)", "HMC (Horizontal Machining Center)",
            "5-Axis Machining", "VTL (Vertical Turret Lathe)", "Conventional Lathe", "Conventional Milling",
            "Boring Machine", "Shaping Machine", "Gear Manufacturing", "Grinding", "EDM",
            "Drilling Machine", "Laser Cutting", "Plasma/Waterjet Cutting", "Sheet Metal/Press",
            "Welding", "Heat Treatment", "Surface Treatment", "Inspection/CMM", "Additive Manufacturing"
        ],
        "valid_materials": [
            "Aluminum", "Steel", "Stainless Steel", "Carbon Steel", "Brass", "Copper",
            "Titanium", "Inconel", "Plastic", "Cast Iron", "Bronze", "Other"
        ]
    }

@api_router.post("/machines/bulk-import")
async def bulk_import_machines(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Bulk import machines from CSV file.
    Valid rows are imported, invalid rows are skipped with error details.
    """
    if user["role"] != UserRole.VENDOR:
        raise HTTPException(status_code=403, detail="Only vendors can import machines")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile required")
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    # Read file content
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Parse CSV
    reader = csv.DictReader(StringIO(content_str))
    
    results = {
        "total_rows": 0,
        "successful": 0,
        "failed": 0,
        "machines_created": [],
        "errors": []
    }
    
    # Valid materials list
    valid_materials = ["Aluminum", "Steel", "Stainless Steel", "Carbon Steel", "Brass", 
                       "Copper", "Titanium", "Inconel", "Plastic", "Cast Iron", "Bronze", "Other"]
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
        results["total_rows"] += 1
        
        # Validate required fields
        errors = []
        
        machine_type = row.get('machine_type', '').strip()
        brand = row.get('brand', '').strip()
        model = row.get('model', '').strip()
        
        if not machine_type:
            errors.append("machine_type is required")
        if not brand:
            errors.append("brand is required")
        if not model:
            errors.append("model is required")
        
        # Parse numeric fields
        numeric_fields = {
            'max_x': 0, 'max_y': 0, 'max_z': 0,
            'max_diameter': 0, 'max_length': 0, 'max_swing': 0,
            'tolerance': 0.01, 'monthly_capacity_hours': 160,
            'bore_diameter': 0, 'outer_diameter': 0, 'max_thickness': 0,
            'tonnage': 0, 'max_taper_angle': 0, 'laser_power': 0,
            'amperage': 0, 'max_temp': 0, 'accuracy': 0,
            'layer_thickness': 0, 'max_module': 0, 'min_teeth': 0,
            'a_axis_range': 0, 'c_axis_range': 0, 'table_diameter': 0,
            'table_size_x': 0, 'table_size_y': 0, 'pallet_size': 0,
            'max_weight': 0, 'spindle_bore': 0, 'spindle_travel': 0,
            'arm_length': 0, 'max_depth': 0, 'max_stroke': 0, 'stroke': 0
        }
        
        parsed_values = {}
        for field, default in numeric_fields.items():
            value = row.get(field, '').strip()
            if value:
                try:
                    if field in ['min_teeth']:
                        parsed_values[field] = int(float(value))
                    else:
                        parsed_values[field] = float(value)
                except ValueError:
                    errors.append(f"Invalid number for {field}: {value}")
            else:
                parsed_values[field] = default
        
        # Parse materials
        materials_str = row.get('materials_supported', '').strip()
        materials = []
        if materials_str:
            materials = [m.strip() for m in materials_str.split(',') if m.strip()]
            # Validate materials
            for mat in materials:
                if mat not in valid_materials:
                    # Try case-insensitive match
                    matched = False
                    for valid_mat in valid_materials:
                        if mat.lower() == valid_mat.lower():
                            materials[materials.index(mat)] = valid_mat
                            matched = True
                            break
                    if not matched:
                        errors.append(f"Unknown material: {mat}")
        
        # If there are validation errors, skip this row
        if errors:
            results["failed"] += 1
            results["errors"].append({
                "row": row_num,
                "data": {k: v for k, v in row.items() if v},
                "errors": errors
            })
            continue
        
        # Create machine document
        machine_id = f"machine_{uuid.uuid4().hex[:12]}"
        name = row.get('name', '').strip() or f"{machine_type} - {brand} {model}"
        machine_category = row.get('machine_category', '').strip()
        
        machine_doc = {
            "machine_id": machine_id,
            "vendor_id": vendor["vendor_id"],
            "name": name,
            "machine_category": machine_category,
            "machine_type": machine_type,
            "brand": brand,
            "model": model,
            "materials_supported": materials,
            "is_active": True,
            "availability_status": "available",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add numeric fields
        for field, value in parsed_values.items():
            if value != 0 or field in ['tolerance', 'monthly_capacity_hours']:
                machine_doc[field] = value
        
        # Insert into database
        try:
            await db.machines.insert_one(machine_doc)
            results["successful"] += 1
            results["machines_created"].append({
                "machine_id": machine_id,
                "name": name,
                "machine_type": machine_type,
                "brand": brand,
                "model": model
            })
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "row": row_num,
                "data": {k: v for k, v in row.items() if v},
                "errors": [f"Database error: {str(e)}"]
            })
    
    logger.info(f"Bulk import completed for vendor {vendor['vendor_id']}: {results['successful']} machines created")
    
    return results

# ============== RFQ ROUTES ==============

@api_router.post("/rfqs", response_model=RFQ)
async def create_rfq(rfq: RFQCreate, user: dict = Depends(get_current_user)):
    rfq_id = f"rfq_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    rfq_doc = {
        "rfq_id": rfq_id,
        "buyer_id": user["user_id"],
        **rfq.model_dump(),
        "status": RFQStatus.DRAFT,
        "drawing_ids": [],
        "ai_analysis": None,
        "matched_vendors": [],
        "created_at": now,
        "updated_at": now
    }
    
    await db.rfqs.insert_one(rfq_doc)
    
    # Send admin notification for new RFQ
    asyncio.create_task(send_admin_notification("new_rfq", {
        "rfq_id": rfq_id,
        "title": rfq.title,
        "buyer_name": user.get("name", "Unknown"),
        "buyer_email": user.get("email", ""),
        "material_type": rfq.material_type,
        "quantity": rfq.quantity,
        "created_at": now
    }))
    
    return RFQ(**rfq_doc)

@api_router.get("/rfqs")
async def list_rfqs(user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.BUYER:
        rfqs = await db.rfqs.find({"buyer_id": user["user_id"]}, {"_id": 0}).to_list(100)
    elif user["role"] == UserRole.VENDOR:
        vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if not vendor or not vendor.get("is_approved"):
            return []
        # Get RFQs where this vendor is matched
        rfqs = await db.rfqs.find(
            {"matched_vendors.vendor_id": vendor["vendor_id"], "status": {"$in": [RFQStatus.MATCHING, RFQStatus.QUOTED]}},
            {"_id": 0}
        ).to_list(100)
    else:
        # Admin sees all
        rfqs = await db.rfqs.find({}, {"_id": 0}).to_list(100)
    
    return rfqs

@api_router.get("/rfqs/{rfq_id}")
async def get_rfq(rfq_id: str, user: dict = Depends(get_current_user)):
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return rfq

@api_router.put("/rfqs/{rfq_id}")
async def update_rfq(rfq_id: str, rfq: RFQCreate, user: dict = Depends(get_current_user)):
    result = await db.rfqs.update_one(
        {"rfq_id": rfq_id, "buyer_id": user["user_id"]},
        {"$set": {**rfq.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    updated = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    return updated

# ============== DRAWING UPLOAD & AI ANALYSIS ==============

@api_router.post("/rfqs/{rfq_id}/drawings")
async def upload_drawing(
    rfq_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload a drawing file for an RFQ - stores in AWS S3"""
    from app.services.s3_storage_service import upload_file
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Read file content
    content = await file.read()
    
    # Check file size (max 25MB for drawings)
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Drawing file size must be less than 25MB")
    
    drawing_id = f"drawing_{uuid.uuid4().hex[:12]}"
    
    # Upload to AWS S3
    try:
        result = upload_file(
            data=content,
            filename=file.filename,
            folder=f"drawings/{rfq_id}",
            content_type=file.content_type or "application/octet-stream"
        )
        s3_url = result["url"]
        s3_path = result["path"]
        logger.info(f"Drawing uploaded to S3: {s3_path}")
    except Exception as e:
        logger.error(f"S3 upload failed for drawing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload drawing to storage: {str(e)}")
    
    drawing_doc = {
        "drawing_id": drawing_id,
        "rfq_id": rfq_id,
        "filename": file.filename,
        "file_type": file.content_type or "application/octet-stream",
        "file_size": len(content),
        "s3_url": s3_url,  # S3 public URL
        "s3_path": s3_path,  # S3 key for deletion/retrieval
        "file_data": None,  # No longer storing base64 in MongoDB
        "ai_analysis": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.drawings.insert_one(drawing_doc)
    
    # Add drawing ID to RFQ
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$push": {"drawing_ids": drawing_id}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"drawing_id": drawing_id, "filename": file.filename, "file_size": len(content), "url": s3_url}

@api_router.get("/rfqs/{rfq_id}/drawings")
async def list_drawings(rfq_id: str, user: dict = Depends(get_current_user)):
    drawings = await db.drawings.find(
        {"rfq_id": rfq_id},
        {"_id": 0, "file_data": 0}  # Exclude large base64 data
    ).to_list(20)
    return drawings

@api_router.get("/drawings/{drawing_id}")
async def get_drawing(drawing_id: str, user: dict = Depends(get_current_user)):
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    return drawing

@api_router.get("/drawings/{drawing_id}/view")
@api_router.head("/drawings/{drawing_id}/view")
async def view_drawing(drawing_id: str, token: Optional[str] = None, request: Request = None):
    """View/download the actual drawing file - supports S3 storage and legacy base64"""
    from app.services.s3_storage_service import download_file
    from fastapi.responses import RedirectResponse
    
    # Try to authenticate via query token or header
    auth_token = token
    if not auth_token and request:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]
    
    # Allow temporary WhatsApp access token
    is_wa_access = auth_token == "wa_temp"
    
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not is_wa_access:
        try:
            payload = jwt.decode(auth_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
    # Check for S3 storage (new drawings)
    s3_url = drawing.get("s3_url")
    s3_path = drawing.get("s3_path")
    
    if s3_url:
        # Redirect to S3 URL or fetch from S3
        if s3_path:
            try:
                file_bytes, content_type = download_file(s3_path)
                filename = drawing.get("filename", f"drawing.pdf")
                return StreamingResponse(
                    iter([file_bytes]),
                    media_type=content_type,
                    headers={
                        "Content-Disposition": f'inline; filename="{filename}"',
                        "Content-Length": str(len(file_bytes))
                    }
                )
            except Exception as e:
                logger.error(f"Failed to download drawing from S3: {e}")
                # Try direct S3 URL redirect as fallback
                return RedirectResponse(url=s3_url)
        else:
            return RedirectResponse(url=s3_url)
    
    # Legacy: base64 stored in MongoDB
    file_data = drawing.get("file_data")
    if not file_data:
        raise HTTPException(status_code=404, detail="Drawing file data not found")
    
    # Remove base64 prefix if present
    if "," in file_data:
        file_data = file_data.split(",")[1]
    
    # Decode base64
    try:
        file_bytes = base64.b64decode(file_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decode file")
    
    # Determine content type
    file_type = drawing.get("file_type", "application/octet-stream")
    content_type_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "pdf": "application/pdf",
        "step": "application/step",
        "stp": "application/step",
        "dxf": "application/dxf",
        "dwg": "application/dwg"
    }
    content_type = content_type_map.get(file_type.lower(), "application/octet-stream")
    
    filename = drawing.get("filename", f"drawing.{file_type}")
    
    return StreamingResponse(
        iter([file_bytes]),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(file_bytes))
        }
    )

@api_router.get("/drawings/{drawing_id}/download")
async def download_drawing(drawing_id: str, user: dict = Depends(get_current_user)):
    """Download the drawing file as attachment - supports S3 storage and legacy base64"""
    from app.services.s3_storage_service import download_file
    from fastapi.responses import RedirectResponse
    
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
    filename = drawing.get("filename", "drawing.pdf")
    
    # Check for S3 storage (new drawings)
    s3_url = drawing.get("s3_url")
    s3_path = drawing.get("s3_path")
    
    if s3_url:
        if s3_path:
            try:
                file_bytes, content_type = download_file(s3_path)
                return StreamingResponse(
                    iter([file_bytes]),
                    media_type="application/octet-stream",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Content-Length": str(len(file_bytes))
                    }
                )
            except Exception as e:
                logger.error(f"Failed to download drawing from S3: {e}")
                return RedirectResponse(url=s3_url)
        else:
            return RedirectResponse(url=s3_url)
    
    # Legacy: base64 stored in MongoDB
    file_data = drawing.get("file_data")
    if not file_data:
        raise HTTPException(status_code=404, detail="Drawing file data not found")
    
    # Remove base64 prefix if present
    if "," in file_data:
        file_data = file_data.split(",")[1]
    
    # Decode base64
    try:
        file_bytes = base64.b64decode(file_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decode file")
    
    return StreamingResponse(
        iter([file_bytes]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_bytes))
        }
    )

def convert_pdf_to_image_base64(pdf_base64: str) -> str:
    """Convert PDF to image for AI analysis"""
    import fitz  # PyMuPDF
    from PIL import Image
    import io
    
    # Decode PDF
    pdf_bytes = base64.b64decode(pdf_base64)
    
    # Open PDF with PyMuPDF
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Get first page
    page = pdf_document[0]
    
    # Render page to image (high resolution for better OCR)
    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    pdf_document.close()
    return img_base64

@api_router.post("/rfqs/{rfq_id}/analyze")
async def analyze_rfq_drawings(rfq_id: str, user: dict = Depends(get_current_user)):
    """Use AI to analyze the uploaded drawings (supports PDF, PNG, JPG). 
    Analyzes multiple drawings together, skips unsupported CAD files but keeps them as attachments."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    if not rfq.get("drawing_ids"):
        raise HTTPException(status_code=400, detail="No drawings uploaded")
    
    # Update status
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {"status": RFQStatus.ANALYZING, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get ALL drawings for this RFQ
    all_drawings = await db.drawings.find(
        {"drawing_id": {"$in": rfq["drawing_ids"]}}, 
        {"_id": 0}
    ).to_list(50)
    
    if not all_drawings:
        raise HTTPException(status_code=404, detail="Drawings not found")
    
    # Categorize drawings: analyzable vs CAD attachments
    unsupported_cad_formats = [".dwg", ".dxf", ".step", ".stp", ".iges", ".igs", ".sat", ".prt", ".sldprt", ".catpart", ".x_t", ".x_b"]
    
    analyzable_drawings = []
    skipped_cad_files = []
    
    for drawing in all_drawings:
        filename = drawing.get("filename", "").lower()
        file_type = drawing.get("file_type", "").lower()
        
        is_unsupported_cad = any(filename.endswith(ext) for ext in unsupported_cad_formats)
        
        if is_unsupported_cad:
            skipped_cad_files.append({
                "drawing_id": drawing["drawing_id"],
                "filename": drawing.get("filename", "Unknown"),
                "reason": "Native CAD format - kept as attachment"
            })
            # Mark as attachment in DB
            await db.drawings.update_one(
                {"drawing_id": drawing["drawing_id"]},
                {"$set": {"is_cad_attachment": True, "analyzed": False}}
            )
        else:
            analyzable_drawings.append(drawing)
    
    # If no analyzable drawings, return info about attachments
    if not analyzable_drawings:
        await db.rfqs.update_one(
            {"rfq_id": rfq_id},
            {"$set": {
                "status": RFQStatus.MATCHING,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "cad_attachments": skipped_cad_files
            }}
        )
        return {
            "message": "No analyzable drawings found",
            "analyzed_count": 0,
            "skipped_cad_files": skipped_cad_files,
            "part_geometry": "unknown",
            "dimensions_missing": True,
            "required_dimensions": ["length", "width", "height"],
            "missing_fields": {"length": True, "width": True, "height": True},
            "note": "All uploaded files are native CAD formats. Please export at least one drawing as PDF or image for AI analysis. CAD files are kept as attachments for vendor reference."
        }
    
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        # Process all analyzable drawings and collect image contents
        image_contents = []
        analyzed_files = []
        
        for drawing in analyzable_drawings:
            file_type = drawing.get("file_type", "").lower()
            filename = drawing.get("filename", "").lower()
            
            try:
                # Get file data - from S3 or legacy base64
                s3_path = drawing.get("s3_path")
                file_data = drawing.get("file_data")
                
                if s3_path:
                    # Fetch from S3
                    from app.services.s3_storage_service import download_file
                    try:
                        file_bytes, _ = download_file(s3_path)
                        file_data = base64.b64encode(file_bytes).decode('utf-8')
                        logger.info(f"Fetched drawing from S3 for analysis: {filename}")
                    except Exception as s3_err:
                        logger.error(f"Failed to fetch drawing from S3: {s3_err}")
                        skipped_cad_files.append({
                            "drawing_id": drawing["drawing_id"],
                            "filename": drawing.get("filename", "Unknown"),
                            "reason": f"S3 fetch error: {str(s3_err)}"
                        })
                        continue
                
                if not file_data:
                    logger.warning(f"No file data available for drawing: {filename}")
                    continue
                
                # Convert PDF to image if needed
                if "pdf" in file_type or filename.endswith(".pdf"):
                    logger.info(f"Converting PDF to image for analysis: {filename}")
                    file_data = convert_pdf_to_image_base64(file_data)
                
                # Verify the file is analyzable
                supported_image_types = ["image/png", "image/jpg", "image/jpeg", "image/gif", "image/webp"]
                is_image = any(img_type in file_type for img_type in supported_image_types) or \
                           filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
                is_pdf = "pdf" in file_type or filename.endswith(".pdf")
                
                if is_image or is_pdf:
                    image_contents.append(ImageContent(image_base64=file_data))
                    analyzed_files.append({
                        "drawing_id": drawing["drawing_id"],
                        "filename": drawing.get("filename", "Unknown")
                    })
                    # Mark as analyzed in DB
                    await db.drawings.update_one(
                        {"drawing_id": drawing["drawing_id"]},
                        {"$set": {"analyzed": True, "is_cad_attachment": False}}
                    )
            except Exception as conv_err:
                logger.error(f"Error processing {filename}: {conv_err}")
                skipped_cad_files.append({
                    "drawing_id": drawing["drawing_id"],
                    "filename": drawing.get("filename", "Unknown"),
                    "reason": f"Processing error: {str(conv_err)}"
                })
        
        if not image_contents:
            raise HTTPException(status_code=400, detail="No valid images could be extracted for analysis")
        
        # Create AI chat for multi-drawing analysis
        chat = LlmChat(
            api_key=api_key,
            session_id=f"analysis_{rfq_id}_{uuid.uuid4().hex[:8]}",
            system_message=f"""You are an expert manufacturing engineer analyzing {len(image_contents)} engineering drawing(s). 
            CAREFULLY examine every detail in ALL drawings including dimension callouts, tolerances, notes, and title blocks.
            
            If multiple drawings are provided, they may show:
            - Different views of the same part (front, top, side, isometric)
            - Assembly drawings with multiple components
            - Detail views with specific features
            
            Combine information from ALL drawings to get complete specifications.
            
            FIRST, identify the part geometry type, then extract appropriate dimensions.
            
            Extract and provide the following information in JSON format:
            {{
                "part_geometry": string - one of: "rectangular", "cylindrical", "circular_flat", "conical", "spherical", "complex", "sheet_metal", "tube_pipe",
                "overall_dimensions": {{
                    // For RECTANGULAR parts (blocks, brackets, housings):
                    "length": float or null,
                    "width": float or null, 
                    "height": float or null,
                    
                    // For CYLINDRICAL parts (shafts, pins, bushings):
                    "diameter": float or null,
                    "outer_diameter": float or null,
                    "inner_diameter": float or null,
                    "length": float or null,
                    
                    // For CIRCULAR FLAT parts (discs, flanges, plates):
                    "diameter": float or null,
                    "thickness": float or null,
                    "bore_diameter": float or null,
                    "pcd": float or null,
                    
                    // For CONICAL parts:
                    "large_diameter": float or null,
                    "small_diameter": float or null,
                    "length": float or null,
                    "taper_angle": float or null,
                    
                    // For TUBE/PIPE:
                    "outer_diameter": float or null,
                    "inner_diameter": float or null,
                    "wall_thickness": float or null,
                    "length": float or null,
                    
                    // For SHEET METAL:
                    "length": float or null,
                    "width": float or null,
                    "thickness": float or null,
                    "bend_radius": float or null,
                    "bend_angle": float or null,
                    
                    "unit": "mm"
                }},
                "critical_tolerances": [{{"feature": string, "tolerance": float, "unit": "mm"}}],
                "holes": [{{"diameter": float, "depth": float or null for THRU, "quantity": int, "type": "plain/threaded/counterbored/countersunk"}}],
                "threads": [{{"type": string, "size": string, "pitch": float or null, "quantity": int}}],
                "radii_fillets": [{{"radius": float, "location": string}}],
                "angles": [{{"angle": float, "feature": string}}],
                "material_specs": string or null,
                "surface_finish": string or null,
                "recommended_processes": [string] - BE SPECIFIC based on features seen,
                "complexity_score": int (1-10),
                "estimated_machining_time_hours": float,
                "special_requirements": [string],
                "max_dimension_mm": float - the largest dimension for machine envelope matching,
                "max_diameter_mm": float or null - for rotational parts,
                "drawings_analyzed": int - number of drawings you analyzed
            }}
            
            IMPORTANT RULES:
            1. Read ALL dimension callouts carefully from ALL drawings
            2. Cross-reference dimensions between different views
            3. Identify the PRIMARY geometry type first
            4. Only populate dimension fields relevant to that geometry
            5. For cylindrical/turned parts, ALWAYS extract diameter and length
            6. For flat circular parts (flanges, discs), extract diameter and thickness
            7. Look for angles, tapers, and radii - these are critical for machining
            8. Check title block for material specs
            9. For recommended_processes, list SPECIFIC operations"""
        ).with_model("openai", "gpt-5.2")
        
        # Get RFQ description for additional context
        rfq_title = rfq.get('title', '')
        rfq_description = rfq.get('description', '')
        
        # Create user message with ALL images for multi-drawing analysis
        drawing_count = len(image_contents)
        user_message = UserMessage(
            text=f"""CAREFULLY analyze these {drawing_count} engineering drawing(s) and extract ALL manufacturing specifications.
            Combine information from all views/drawings to get complete dimensions.
            
            === RFQ CONTEXT (Use this to help identify part type and dimensions) ===
            Title: {rfq_title}
            Description: {rfq_description}
            Material Type: {rfq['material_type']}
            Required Tolerance: {rfq['tolerance']} mm
            Quantity: {rfq['quantity']}
            
            === IMPORTANT ===
            - If dimensions are NOT clearly visible in the drawings, try to INFER them from:
              1. The title (e.g., "50mm Shaft" suggests diameter=50mm)
              2. The description (e.g., "200mm length x 100mm diameter" gives specific dimensions)
              3. Standard part sizes mentioned
            - Mark inferred dimensions with a note in special_requirements
            - Even if drawings are unclear, provide your BEST ESTIMATE based on all available context
            
            Files being analyzed: {', '.join([f['filename'] for f in analyzed_files])}
            
            Please provide a detailed analysis in the JSON format specified.""",
            file_contents=image_contents
        )
        
        response = await chat.send_message(user_message)
        
        # Parse the response to extract JSON
        import json
        import re
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            ai_analysis = json.loads(json_match.group())
        else:
            ai_analysis = {
                "raw_analysis": response,
                "error": "Could not parse structured data"
            }
        
        # Add metadata about analysis
        ai_analysis["analyzed_files"] = analyzed_files
        ai_analysis["skipped_cad_files"] = skipped_cad_files
        
        # Update all analyzed drawings with analysis
        for af in analyzed_files:
            await db.drawings.update_one(
                {"drawing_id": af["drawing_id"]},
                {"$set": {"ai_analysis": ai_analysis, "analyzed": True}}
            )
        
        # Update RFQ with analysis
        await db.rfqs.update_one(
            {"rfq_id": rfq_id},
            {"$set": {
                "ai_analysis": ai_analysis,
                "status": RFQStatus.MATCHING,
                "cad_attachments": skipped_cad_files,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Check if dimensions are missing based on geometry type
        dims = ai_analysis.get("overall_dimensions", {})
        part_geometry = ai_analysis.get("part_geometry", "rectangular")
        
        # ============== FALLBACK: Extract dimensions from title/description ==============
        # If AI couldn't extract dimensions, try to parse from text
        def extract_dimensions_from_text(title, description):
            """Extract dimensions mentioned in title or description"""
            import re
            text = f"{title} {description}".lower()
            extracted = {}
            
            # Pattern for dimensions like "100mm", "50 mm", "200 x 100", etc.
            # Diameter patterns: "dia 50mm", "diameter 100mm", "Ø50", "50mm dia"
            dia_patterns = [
                r'(?:dia(?:meter)?|ø)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?',
                r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:dia(?:meter)?|ø)',
                r'd\s*[:=]\s*(\d+(?:\.\d+)?)\s*(?:mm)?'
            ]
            for pattern in dia_patterns:
                match = re.search(pattern, text)
                if match:
                    extracted['diameter'] = float(match.group(1))
                    break
            
            # Length patterns: "length 200mm", "L=150", "200mm long"
            length_patterns = [
                r'(?:length|long|l)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?',
                r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:length|long)',
            ]
            for pattern in length_patterns:
                match = re.search(pattern, text)
                if match:
                    extracted['length'] = float(match.group(1))
                    break
            
            # Width patterns
            width_patterns = [
                r'(?:width|w)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?',
                r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:wide|width)',
            ]
            for pattern in width_patterns:
                match = re.search(pattern, text)
                if match:
                    extracted['width'] = float(match.group(1))
                    break
            
            # Height/thickness patterns
            height_patterns = [
                r'(?:height|thickness|h|t)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?',
                r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:thick|height)',
            ]
            for pattern in height_patterns:
                match = re.search(pattern, text)
                if match:
                    val = float(match.group(1))
                    if 'thickness' in text or 'thick' in text:
                        extracted['thickness'] = val
                    else:
                        extracted['height'] = val
                    break
            
            # Dimension format: "100 x 50 x 25" or "100x50x25 mm"
            dim_pattern = r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:[xX×]\s*(\d+(?:\.\d+)?))?\s*(?:mm)?'
            match = re.search(dim_pattern, text)
            if match:
                vals = [float(v) for v in match.groups() if v]
                if len(vals) >= 2:
                    sorted_vals = sorted(vals, reverse=True)
                    if 'length' not in extracted:
                        extracted['length'] = sorted_vals[0]
                    if 'width' not in extracted and len(sorted_vals) > 1:
                        extracted['width'] = sorted_vals[1]
                    if 'height' not in extracted and len(sorted_vals) > 2:
                        extracted['height'] = sorted_vals[2]
            
            # OD/ID patterns for pipes/tubes
            od_match = re.search(r'(?:od|outer\s*(?:dia(?:meter)?)?)\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
            if od_match:
                extracted['outer_diameter'] = float(od_match.group(1))
            
            id_match = re.search(r'(?:id|inner\s*(?:dia(?:meter)?)?|bore)\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
            if id_match:
                extracted['inner_diameter'] = float(id_match.group(1))
            
            return extracted
        
        # Try to fill in missing dimensions from title/description
        text_dims = extract_dimensions_from_text(rfq.get('title', ''), rfq.get('description', ''))
        
        if text_dims:
            logger.info(f"Extracted dimensions from title/description: {text_dims}")
            # Merge with AI-extracted dimensions (AI takes precedence)
            for key, value in text_dims.items():
                if not dims.get(key) or dims.get(key) == 0:
                    dims[key] = value
                    if "dimensions_from_text" not in ai_analysis.get("special_requirements", []):
                        if "special_requirements" not in ai_analysis:
                            ai_analysis["special_requirements"] = []
                        ai_analysis["special_requirements"].append(f"Dimension '{key}' extracted from RFQ text")
            
            # Update the analysis with merged dimensions
            ai_analysis["overall_dimensions"] = dims
            ai_analysis["text_extracted_dimensions"] = text_dims
            
            # Update in database
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$set": {"ai_analysis": ai_analysis}}
            )
        
        # Define required dimensions for each geometry type
        geometry_requirements = {
            "rectangular": ["length", "width", "height"],
            "cylindrical": ["diameter", "length"],
            "circular_flat": ["diameter", "thickness"],
            "conical": ["large_diameter", "small_diameter", "length"],
            "spherical": ["diameter"],
            "tube_pipe": ["outer_diameter", "inner_diameter", "length"],
            "sheet_metal": ["length", "width", "thickness"],
            "complex": ["max_dimension_mm"]  # For complex parts, just need max dimension
        }
        
        required_dims = geometry_requirements.get(part_geometry, ["length", "width", "height"])
        
        # Check which required dimensions are missing
        missing_fields = {}
        has_all_required = True
        for dim in required_dims:
            value = dims.get(dim) or ai_analysis.get(dim)
            is_missing = not (value and value > 0)
            missing_fields[dim] = is_missing
            if is_missing:
                has_all_required = False
        
        dimensions_missing = not has_all_required
        
        return {
            "message": f"Analysis complete - analyzed {len(analyzed_files)} drawing(s)", 
            "analysis": ai_analysis,
            "part_geometry": part_geometry,
            "dimensions_missing": dimensions_missing,
            "required_dimensions": required_dims,
            "missing_fields": missing_fields,
            "analyzed_count": len(analyzed_files),
            "analyzed_files": analyzed_files,
            "skipped_cad_files": skipped_cad_files
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like unsupported file format) without fallback
        raise
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        # Provide fallback analysis for other errors
        fallback_analysis = {
            "overall_dimensions": {"length": None, "width": None, "height": None, "unit": "mm"},
            "critical_tolerances": [],
            "holes": [],
            "threads": [],
            "material_specs": rfq["material_type"],
            "surface_finish": rfq.get("surface_finish"),
            "recommended_processes": ["CNC Milling", "CNC Turning"],
            "complexity_score": 5,
            "estimated_machining_time_hours": 2.0,
            "special_requirements": [],
            "error": str(e)
        }
        
        await db.rfqs.update_one(
            {"rfq_id": rfq_id},
            {"$set": {
                "ai_analysis": fallback_analysis,
                "status": RFQStatus.MATCHING,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "message": "Analysis complete with fallback", 
            "analysis": fallback_analysis,
            "part_geometry": "unknown",
            "dimensions_missing": True,
            "required_dimensions": ["length", "width", "height"],
            "missing_fields": {"length": True, "width": True, "height": True}
        }

# ============== MANUAL DIMENSIONS UPDATE ==============

class ManualDimensions(BaseModel):
    # Rectangular dimensions
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    # Cylindrical/Circular dimensions
    diameter: Optional[float] = None
    outer_diameter: Optional[float] = None
    inner_diameter: Optional[float] = None
    thickness: Optional[float] = None
    # Conical dimensions
    large_diameter: Optional[float] = None
    small_diameter: Optional[float] = None
    taper_angle: Optional[float] = None
    # Sheet metal
    bend_radius: Optional[float] = None
    bend_angle: Optional[float] = None
    # Common
    weight: Optional[float] = None  # Optional weight in kg
    part_geometry: Optional[str] = None  # Allow changing geometry type

@api_router.put("/rfqs/{rfq_id}/dimensions")
async def update_rfq_dimensions(
    rfq_id: str, 
    dimensions: ManualDimensions,
    user: dict = Depends(get_current_user)
):
    """Update RFQ dimensions manually when AI couldn't extract them from drawing"""
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get current AI analysis or create empty one
    ai_analysis = rfq.get("ai_analysis") or {}
    overall_dimensions = ai_analysis.get("overall_dimensions") or {}
    
    # Update part geometry if provided
    if dimensions.part_geometry:
        ai_analysis["part_geometry"] = dimensions.part_geometry
    
    # Update ALL dimension fields with provided values
    dimension_fields = [
        "length", "width", "height",  # Rectangular
        "diameter", "outer_diameter", "inner_diameter", "thickness",  # Cylindrical/Circular
        "large_diameter", "small_diameter", "taper_angle",  # Conical
        "bend_radius", "bend_angle"  # Sheet metal
    ]
    
    for field in dimension_fields:
        value = getattr(dimensions, field, None)
        if value is not None:
            overall_dimensions[field] = value
    
    overall_dimensions["unit"] = "mm"
    
    # Add weight if provided
    if dimensions.weight is not None:
        ai_analysis["weight_kg"] = dimensions.weight
    
    # Calculate max dimension for envelope matching (consider all dimension types)
    dim_values = [
        overall_dimensions.get("length") or 0,
        overall_dimensions.get("width") or 0,
        overall_dimensions.get("height") or 0,
        overall_dimensions.get("diameter") or 0,
        overall_dimensions.get("outer_diameter") or 0,
        overall_dimensions.get("large_diameter") or 0,
        overall_dimensions.get("thickness") or 0
    ]
    ai_analysis["max_dimension_mm"] = max(dim_values) if any(dim_values) else None
    
    # Also set max_diameter_mm for rotational parts
    diameter_values = [
        overall_dimensions.get("diameter") or 0,
        overall_dimensions.get("outer_diameter") or 0,
        overall_dimensions.get("large_diameter") or 0
    ]
    if any(diameter_values):
        ai_analysis["max_diameter_mm"] = max(diameter_values)
    
    ai_analysis["overall_dimensions"] = overall_dimensions
    ai_analysis["dimensions_manually_updated"] = True
    
    # Update the RFQ
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {
            "ai_analysis": ai_analysis,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    part_geometry = ai_analysis.get("part_geometry", "rectangular")
    logger.info(f"Dimensions updated for RFQ {rfq_id} ({part_geometry}): {overall_dimensions}")
    
    return {
        "message": "Dimensions updated successfully",
        "part_geometry": part_geometry,
        "overall_dimensions": overall_dimensions,
        "max_dimension_mm": ai_analysis.get("max_dimension_mm"),
        "max_diameter_mm": ai_analysis.get("max_diameter_mm")
    }


# ============== HELPER: Send RFQ Drawings to Vendor ==============

async def send_rfq_drawings_to_vendor(phone: str, rfq_id: str, drawing_ids: list, rfq_title: str):
    """
    Send RFQ drawing files to a vendor via WhatsApp
    Called after RFQ match notification
    Uses preview images to avoid Meta content moderation issues with PDFs
    """
    from app.services.whatsapp_service import send_image_message
    
    # Use the actual deployed URL
    BASE_URL = os.environ.get("APP_URL", "https://rfq-marketplace-9.preview.emergentagent.com")
    
    # Small delay to let template message send first
    await asyncio.sleep(2)
    
    for i, drawing_id in enumerate(drawing_ids[:3]):  # Limit to 3 drawings
        try:
            drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
            if not drawing:
                logger.warning(f"Drawing {drawing_id} not found in database")
                continue
                
            filename = drawing.get("filename", f"drawing_{i+1}.pdf")
            
            # Check if preview image exists (converted from PDF)
            preview_url = drawing.get("preview_url")
            
            if preview_url:
                # Use the stored preview image URL
                image_url = preview_url
            else:
                # Use the preview endpoint which returns a PNG
                image_url = f"{BASE_URL}/api/drawings/{drawing_id}/preview?token=wa_temp"
            
            caption = f"📐 *{filename}*\n📋 RFQ: {rfq_title[:40]}\n\n🔗 Full drawing: {BASE_URL}/vendor/rfq/{rfq_id}"
            
            logger.info(f"Sending drawing preview {drawing_id} to {phone[:6]}***: {image_url}")
            
            result = await send_image_message(phone, image_url, caption)
            
            logger.info(f"Drawing preview send result: {result}")
            
            # Small delay between files
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error sending drawing {drawing_id} to {phone[:6]}***: {str(e)}")


# ============== VENDOR MATCHING ==============

@api_router.post("/rfqs/{rfq_id}/match")
async def match_vendors(rfq_id: str, user: dict = Depends(get_current_user)):
    """
    Enhanced RFQ Matching Algorithm v2.0
    
    Matches RFQ with capable vendors based on:
    1. AI-extracted drawing dimensions and machine envelope validation
    2. Required manufacturing processes vs machine capabilities
    3. Material compatibility
    4. Tolerance capabilities
    5. Job title/description keyword matching
    6. Seller past experience with similar jobs
    """
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get all approved vendors
    vendors = await db.vendors.find({"is_approved": True}, {"_id": 0}).to_list(100)
    
    if not vendors:
        # Return demo vendors for testing
        demo_matches = [
            {
                "vendor_id": "demo_vendor_1",
                "user_id": "demo_user_1",
                "company_name": "Precision CNC Works",
                "suitability_score": 92,
                "matching_machines": ["CNC Milling Center", "5-Axis VMC"],
                "materials_match": True,
                "tolerance_capable": True,
                "dimension_capable": True,
                "process_matches": ["CNC Milling", "5-Axis Machining"],
                "keyword_matches": ["CNC", "Milling"],
                "experience_score": 85,
                "similar_jobs_count": 45,
                "location": "Mumbai, India",
                "rating": 4.8,
                "total_jobs": 156
            }
        ]
        
        await db.rfqs.update_one(
            {"rfq_id": rfq_id},
            {"$set": {
                "matched_vendors": demo_matches,
                "status": RFQStatus.MATCHING,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"matched_vendors": demo_matches, "total_matches": len(demo_matches)}
    
    # ============== EXTRACT RFQ REQUIREMENTS ==============
    ai_analysis = rfq.get("ai_analysis") or {}
    dims = ai_analysis.get("overall_dimensions") or {}
    recommended_processes = ai_analysis.get("recommended_processes", [])
    part_geometry = ai_analysis.get("part_geometry", "rectangular")
    
    # ============== FALLBACK: Extract dimensions from title/description for matching ==============
    def extract_dimensions_for_matching(title, description):
        """Extract dimensions mentioned in title or description for matching when AI analysis is incomplete"""
        import re
        text = f"{title} {description}".lower()
        extracted = {}
        
        # Diameter patterns
        dia_patterns = [
            r'(?:dia(?:meter)?|ø)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?',
            r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:dia(?:meter)?|ø)',
        ]
        for pattern in dia_patterns:
            match = re.search(pattern, text)
            if match:
                extracted['diameter'] = float(match.group(1))
                break
        
        # Length patterns
        length_patterns = [
            r'(?:length|long|l)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:mm)?',
            r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:length|long)',
        ]
        for pattern in length_patterns:
            match = re.search(pattern, text)
            if match:
                extracted['length'] = float(match.group(1))
                break
        
        # Width patterns
        width_match = re.search(r'(?:width|w)\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
        if width_match:
            extracted['width'] = float(width_match.group(1))
        
        # Height/thickness patterns  
        height_match = re.search(r'(?:height|thickness|h|t)\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
        if height_match:
            val = float(height_match.group(1))
            if 'thickness' in text:
                extracted['thickness'] = val
            else:
                extracted['height'] = val
        
        # Dimension format: "100 x 50 x 25" or "100x50x25 mm"
        dim_pattern = r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:[xX×]\s*(\d+(?:\.\d+)?))?\s*(?:mm)?'
        match = re.search(dim_pattern, text)
        if match:
            vals = [float(v) for v in match.groups() if v]
            if len(vals) >= 2:
                sorted_vals = sorted(vals, reverse=True)
                if 'length' not in extracted:
                    extracted['length'] = sorted_vals[0]
                if 'width' not in extracted and len(sorted_vals) > 1:
                    extracted['width'] = sorted_vals[1]
                if 'height' not in extracted and len(sorted_vals) > 2:
                    extracted['height'] = sorted_vals[2]
        
        # OD/ID for pipes
        od_match = re.search(r'(?:od|outer\s*dia(?:meter)?)\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
        if od_match:
            extracted['outer_diameter'] = float(od_match.group(1))
        id_match = re.search(r'(?:id|inner\s*dia(?:meter)?|bore)\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
        if id_match:
            extracted['inner_diameter'] = float(id_match.group(1))
        
        # Weight patterns
        weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|kilos?|kilogram)', text)
        if weight_match:
            extracted['weight_kg'] = float(weight_match.group(1))
        
        return extracted
    
    # Extract dimensions from text if AI analysis is missing dimensions
    text_dims = extract_dimensions_for_matching(rfq.get('title', ''), rfq.get('description', ''))
    dimensions_from_text = False
    
    if text_dims:
        logger.info(f"Matching - Extracted dimensions from title/description: {text_dims}")
        # Merge text dimensions with AI dimensions (AI takes precedence)
        for key, value in text_dims.items():
            if key == 'weight_kg':
                if not ai_analysis.get('weight_kg'):
                    ai_analysis['weight_kg'] = value
                    dimensions_from_text = True
            elif key not in dims or not dims.get(key):
                dims[key] = value
                dimensions_from_text = True
    
    # Get part dimensions from AI analysis based on geometry
    part_length = dims.get("length") or 0
    part_width = dims.get("width") or 0
    part_height = dims.get("height") or 0
    part_diameter = dims.get("diameter") or dims.get("outer_diameter") or ai_analysis.get("max_diameter_mm") or 0
    part_inner_diameter = dims.get("inner_diameter") or dims.get("bore_diameter") or 0
    part_thickness = dims.get("thickness") or part_height or 0
    part_large_diameter = dims.get("large_diameter") or part_diameter or 0
    part_small_diameter = dims.get("small_diameter") or 0
    part_taper_angle = dims.get("taper_angle") or 0
    part_weight = ai_analysis.get("weight_kg") or 0
    
    # Calculate max dimension for envelope check
    max_dimension = ai_analysis.get("max_dimension_mm")
    if not max_dimension:
        dim_values = [part_length, part_width, part_height, part_diameter, part_large_diameter, part_thickness]
        dim_values = [d for d in dim_values if d]
        max_dimension = max(dim_values) if dim_values else None
    
    # Calculate max diameter for turning operations
    max_diameter = ai_analysis.get("max_diameter_mm") or max(part_diameter, part_large_diameter, part_inner_diameter) or 0
    
    required_tolerance = rfq.get("tolerance", 0.1)
    required_material = rfq.get("material_type", "").lower()
    
    # Extract material from AI if available
    ai_material = (ai_analysis.get("material_specs") or "").lower()
    
    # ============== GEOMETRY-BASED PROCESS DETERMINATION ==============
    # Determine required process types based on part geometry
    geometry_process_map = {
        "cylindrical": ["turning", "cnc_turning"],
        "circular_flat": ["turning", "milling", "vtl"],  # Can be turned or milled depending on size
        "conical": ["turning", "cnc_turning"],
        "tube_pipe": ["turning", "boring"],
        "rectangular": ["milling", "cnc_milling"],
        "sheet_metal": ["sheet_metal", "press", "cutting"],
        "complex": ["5axis", "milling"],
        "spherical": ["turning", "5axis"]
    }
    
    required_process_types = geometry_process_map.get(part_geometry, ["milling"])
    
    # Override if specific processes detected from AI analysis
    for proc in recommended_processes:
        proc_lower = proc.lower() if isinstance(proc, str) else ""
        if "turn" in proc_lower or "lathe" in proc_lower:
            if "turning" not in required_process_types:
                required_process_types.insert(0, "turning")
        elif "mill" in proc_lower:
            if "milling" not in required_process_types:
                required_process_types.insert(0, "milling")
        elif "5-axis" in proc_lower or "5 axis" in proc_lower:
            if "5axis" not in required_process_types:
                required_process_types.insert(0, "5axis")
    
    # ============== EXTRACT JOB KEYWORDS FROM TITLE & DESCRIPTION ==============
    job_title = rfq.get("title", "").lower()
    job_description = rfq.get("description", "").lower()
    
    # Manufacturing process keywords to match
    process_keywords = {
        "turning": ["turn", "lathe", "shaft", "spindle", "axle", "rod", "pin", "bushing", "sleeve", "cylinder"],
        "milling": ["mill", "pocket", "slot", "profile", "face", "plate", "block", "bracket", "housing"],
        "drilling": ["drill", "hole", "bore", "tap", "thread"],
        "grinding": ["grind", "finish", "polish", "surface"],
        "gear": ["gear", "hobbing", "spline", "sprocket", "rack", "pinion", "cog"],
        "boring": ["bore", "boring", "ream", "id", "internal"],
        "welding": ["weld", "fabricat", "join", "assembly"],
        "sheet_metal": ["sheet", "bend", "press", "punch", "shear", "fold", "brake"],
        "cutting": ["cut", "laser", "plasma", "waterjet"],
        "vtl": ["vtl", "vertical turret", "large diameter", "ring", "flange", "disc"],
        "5axis": ["5-axis", "5 axis", "complex", "contour", "impeller", "blade", "turbine"],
        "edm": ["edm", "wire cut", "spark", "electrode"],
        "heat_treatment": ["heat treat", "harden", "temper", "anneal", "quench"],
        "cnc": ["cnc", "precision", "accurate", "tight tolerance"]
    }
    
    # Find matching keywords from job title and description
    job_text = f"{job_title} {job_description}"
    detected_keywords = []
    detected_processes = []
    
    for process, keywords in process_keywords.items():
        for keyword in keywords:
            if keyword in job_text:
                detected_keywords.append(keyword)
                if process not in detected_processes:
                    detected_processes.append(process)
    
    logger.info(f"Matching RFQ {rfq_id}: geometry={part_geometry}, dims=L{part_length}xW{part_width}xH{part_height}, dia={part_diameter}, weight={part_weight}kg")
    logger.info(f"Required tolerance={required_tolerance}, material={required_material}")
    logger.info(f"Required process types for geometry: {required_process_types}")
    logger.info(f"Detected keywords: {detected_keywords}, processes: {detected_processes}")
    logger.info(f"AI recommended processes: {recommended_processes}")
    
    matched_vendors = []
    
    # ============== GET RFQ URGENCY FOR SCORING ==============
    rfq_urgency = rfq.get("urgency", "normal")  # urgent, high, normal, low
    rfq_deadline = rfq.get("deadline")
    is_urgent_rfq = rfq_urgency in ["urgent", "high"]
    
    # Urgency score multipliers
    urgency_multipliers = {
        "urgent": 1.25,  # 25% boost for urgent RFQs
        "high": 1.15,    # 15% boost for high priority
        "normal": 1.0,
        "low": 0.95      # Slight reduction for low priority (availability less important)
    }
    urgency_multiplier = urgency_multipliers.get(rfq_urgency, 1.0)
    
    logger.info(f"RFQ urgency: {rfq_urgency}, deadline: {rfq_deadline}, urgency_multiplier: {urgency_multiplier}")
    
    for vendor in vendors:
        # Get vendor's machines
        machines = await db.machines.find(
            {"vendor_id": vendor["vendor_id"], "is_active": True},
            {"_id": 0}
        ).to_list(50)
        
        if not machines:
            continue
        
        # ============== GET VENDOR'S PAST EXPERIENCE (from profile + orders) ==============
        # Get vendor's declared past experiences from profile
        vendor_past_experiences = vendor.get("past_experiences", [])
        
        # Get completed orders for this vendor
        past_orders = await db.orders.find(
            {"vendor_id": vendor["vendor_id"], "status": "completed"},
            {"_id": 0, "rfq_id": 1}
        ).to_list(200)
        
        # Get RFQ details for past orders to analyze experience
        past_rfq_ids = [o["rfq_id"] for o in past_orders]
        past_rfqs = await db.rfqs.find(
            {"rfq_id": {"$in": past_rfq_ids}},
            {"_id": 0, "title": 1, "description": 1, "material_type": 1, "ai_analysis": 1}
        ).to_list(200) if past_rfq_ids else []
        
        # Analyze similar past jobs (including geometry match)
        similar_jobs_count = 0
        experience_keywords_matched = []
        geometry_experience = False
        experience_match_details = []
        material_experience = False
        process_experience = False
        part_type_experience = False
        best_experience_match = None
        best_experience_score = 0
        
        # ============== CHECK VENDOR'S DECLARED PAST EXPERIENCES ==============
        for exp in vendor_past_experiences:
            exp_title = (exp.get("title") or "").lower()
            exp_desc = (exp.get("description") or "").lower()
            exp_material = (exp.get("material") or "").lower()
            exp_industry = (exp.get("industry") or "").lower()
            exp_part_type = (exp.get("part_type") or "").lower()
            exp_processes = [p.lower() for p in exp.get("processes_used", [])]
            exp_text = f"{exp_title} {exp_desc} {exp_industry} {exp_part_type}"
            
            similarity_score = 0
            match_reasons = []
            
            # Check title/description keyword match (more weight for title match)
            job_title_lower = job_title.lower()
            job_desc_lower = job_description.lower()
            
            # Title similarity check
            title_words = set(job_title_lower.split())
            exp_title_words = set(exp_title.split())
            common_title_words = title_words & exp_title_words - {'for', 'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'at', 'by', '-', 'mm', 'kg'}
            if common_title_words:
                similarity_score += len(common_title_words) * 3  # High weight for title match
                match_reasons.append(f"title_match:{list(common_title_words)[:3]}")
            
            # Check keywords match
            for keyword in detected_keywords:
                if keyword in exp_text:
                    similarity_score += 2
                    if keyword not in experience_keywords_matched:
                        experience_keywords_matched.append(keyword)
                    match_reasons.append(f"keyword:{keyword}")
            
            # Check material match (high weight)
            if required_material and required_material in exp_material:
                similarity_score += 5
                material_experience = True
                match_reasons.append(f"material:{required_material}")
            
            # Check process match
            for proc in recommended_processes:
                proc_lower = proc.lower()
                if any(proc_lower in p or p in proc_lower for p in exp_processes):
                    similarity_score += 3
                    process_experience = True
                    match_reasons.append(f"process:{proc}")
            
            # Check part type match (e.g., "shaft", "housing", "bracket")
            if exp_part_type:
                if exp_part_type in job_text:
                    similarity_score += 4
                    part_type_experience = True
                    match_reasons.append(f"part_type:{exp_part_type}")
                # Also check if job mentions the part type
                common_part_types = ["shaft", "housing", "bracket", "flange", "gear", "plate", "block", "sleeve", "bushing", "pin", "rod", "disc", "ring"]
                for pt in common_part_types:
                    if pt in job_text and pt in exp_text:
                        similarity_score += 3
                        part_type_experience = True
                        if f"part:{pt}" not in match_reasons:
                            match_reasons.append(f"part:{pt}")
            
            # Check industry match
            if exp_industry and exp_industry in job_text:
                similarity_score += 2
                match_reasons.append(f"industry:{exp_industry}")
            
            if similarity_score >= 2:
                similar_jobs_count += 1
                exp_detail = {
                    "source": "profile",
                    "title": exp.get("title"),
                    "description": exp.get("description", "")[:100],
                    "material": exp.get("material"),
                    "part_type": exp.get("part_type"),
                    "processes": exp.get("processes_used", []),
                    "year": exp.get("year"),
                    "score": similarity_score,
                    "matches": match_reasons
                }
                experience_match_details.append(exp_detail)
                
                # Track best match
                if similarity_score > best_experience_score:
                    best_experience_score = similarity_score
                    best_experience_match = exp_detail
        
        # ============== CHECK COMPLETED ORDER HISTORY ==============
        for past_rfq in past_rfqs:
            past_title = (past_rfq.get("title") or "").lower()
            past_desc = (past_rfq.get("description") or "").lower()
            past_material = (past_rfq.get("material_type") or "").lower()
            past_text = f"{past_title} {past_desc}"
            past_geometry = (past_rfq.get("ai_analysis") or {}).get("part_geometry", "")
            
            # Check if past job has same geometry
            if past_geometry == part_geometry:
                geometry_experience = True
                similar_jobs_count += 1
            
            # Check if past job is similar based on keywords
            similarity_score = 0
            for keyword in detected_keywords:
                if keyword in past_text:
                    similarity_score += 1
                    if keyword not in experience_keywords_matched:
                        experience_keywords_matched.append(keyword)
            
            # Check material match
            if required_material and required_material in past_material:
                similarity_score += 2
            
            # Check if past job used similar processes
            past_processes = (past_rfq.get("ai_analysis") or {}).get("recommended_processes", [])
            for proc in recommended_processes:
                if any(proc.lower() in p.lower() for p in past_processes):
                    similarity_score += 1
            
            if similarity_score >= 2:
                similar_jobs_count += 1
                experience_match_details.append({
                    "source": "order_history",
                    "title": past_rfq.get("title"),
                    "material": past_rfq.get("material_type"),
                    "geometry": past_geometry,
                    "score": similarity_score
                })
        
        # ============== CALCULATE EXPERIENCE SCORE (max 35 points - increased weightage) ==============
        # Base score from similar jobs
        experience_score = min(similar_jobs_count * 3, 15)  # Up to 15 points for job count
        
        # Bonus for keyword matches
        experience_score += min(len(experience_keywords_matched) * 2, 8)  # Up to 8 points
        
        # Bonus for geometry experience
        if geometry_experience:
            experience_score += 5
        
        # Bonus for material experience (vendor worked with same material before)
        if material_experience:
            experience_score += 4
        
        # Bonus for process experience
        if process_experience:
            experience_score += 3
        
        # Bonus for part type experience (e.g., vendor made shafts before, RFQ is for shaft)
        if part_type_experience:
            experience_score += 5
        
        experience_score = min(experience_score, 35)  # Cap at 35 points
        
        # Track capabilities across all machines
        matching_machines = []
        tolerance_capable = False
        materials_match = False
        dimension_capable = False
        weight_capable = False
        process_matches = []
        keyword_matches = []
        has_suitable_machine = False
        geometry_compatible = False
        rejection_reasons = []
        
        # Track machine availability for urgency scoring
        available_machine_count = 0
        total_matching_machines = 0
        has_available_machine = False
        
        for machine in machines:
            machine_type_lower = machine.get("machine_type", "").lower()
            
            # ============== MACHINE AVAILABILITY CHECK ==============
            machine_availability = machine.get("availability_status", "available")
            is_machine_available = machine_availability == "available"
            
            # For urgent RFQs, strongly prefer available machines
            # For non-urgent, engaged machines can still be considered
            if is_urgent_rfq and not is_machine_available:
                # Skip non-available machines for urgent RFQs unless no alternatives
                engaged_until = machine.get("engaged_until")
                if engaged_until and rfq_deadline:
                    # Check if machine will be available before deadline
                    try:
                        engaged_date = datetime.fromisoformat(engaged_until.replace('Z', '+00:00'))
                        deadline_date = datetime.fromisoformat(rfq_deadline + "T00:00:00+00:00")
                        if engaged_date < deadline_date:
                            # Machine will be free before deadline, can consider
                            is_machine_available = True
                    except:
                        pass
            machine_category = machine.get("machine_category", "").lower()
            machine_name = f"{machine.get('machine_type', '')} - {machine.get('brand', '')} {machine.get('model', '')}"
            machine_score = 0
            machine_process_match = False
            dimension_fit = False
            weight_fit = True
            machine_rejection = None
            
            # ============== MACHINE CATEGORY DETECTION ==============
            is_welding_machine = "weld" in machine_type_lower
            is_turning_machine = any(k in machine_type_lower for k in ["lathe", "turn", "vtl"])
            is_milling_machine = any(k in machine_type_lower for k in ["mill", "vmc", "hmc", "machining center"]) and not is_turning_machine
            is_5axis_machine = "5-axis" in machine_type_lower or "5 axis" in machine_type_lower
            is_gear_machine = "gear" in machine_type_lower or "hob" in machine_type_lower
            is_grinding_machine = "grind" in machine_type_lower
            is_boring_machine = "boring" in machine_type_lower
            is_edm_machine = "edm" in machine_type_lower
            is_drilling_machine = "drill" in machine_type_lower
            is_press_machine = any(k in machine_type_lower for k in ["press", "brake", "sheet"])
            is_cutting_machine = any(k in machine_type_lower for k in ["laser", "plasma", "waterjet", "cut"])
            is_vtl_machine = "vtl" in machine_type_lower or "vertical turret" in machine_type_lower
            
            # ============== CONVENTIONAL/HEAVY MACHINE DETECTION ==============
            is_conventional_lathe = any(k in machine_type_lower for k in ["engine lathe", "turret lathe", "capstan", "gap bed", "heavy duty lathe"])
            is_conventional_mill = any(k in machine_type_lower for k in ["universal milling", "vertical milling", "horizontal milling", "knee mill", "bed mill", "ram turret"])
            is_conventional_machine = is_conventional_lathe or is_conventional_mill or "conventional" in machine_type_lower or "conventional" in machine_category
            is_heavy_duty_machine = any(k in machine_type_lower for k in ["heavy duty", "heavy-duty", "floor boring", "planer", "double column"])
            is_shaping_machine = any(k in machine_type_lower for k in ["shaper", "planer", "slotter"])
            
            # Check if job requires rough/heavy machining
            rough_heavy_keywords = ["rough", "roughing", "heavy", "heavy duty", "heavy-duty", "forging", "casting", "large scale", "heavy machining", "stock removal", "bulk removal"]
            job_needs_rough_heavy = any(k in job_description.lower() for k in rough_heavy_keywords)
            
            # Check if AI analysis recommends conventional/rough machining
            ai_recommends_conventional = any(
                any(k in proc.lower() for k in ["conventional", "rough", "heavy", "shaping", "planing"])
                for proc in recommended_processes
            )
            
            # Bonus for conventional machines when rough/heavy work is needed
            if job_needs_rough_heavy or ai_recommends_conventional:
                if is_conventional_machine or is_heavy_duty_machine or is_shaping_machine:
                    machine_score += 15  # Significant bonus for appropriate machine
                    if "Conventional Machining" not in process_matches:
                        process_matches.append("Conventional Machining")
            
            # ============== GEOMETRY-MACHINE COMPATIBILITY CHECK ==============
            # This ensures milling machines don't match turning jobs and vice versa
            machine_compatible_with_geometry = False
            
            if part_geometry in ["cylindrical", "conical", "tube_pipe"]:
                # These REQUIRE turning machines
                if is_turning_machine or is_vtl_machine or is_boring_machine:
                    machine_compatible_with_geometry = True
                else:
                    machine_rejection = f"Geometry '{part_geometry}' requires turning machine, not {machine_type_lower}"
                    
            elif part_geometry == "circular_flat":
                # Can be turned (disc/flange) or milled (plate with holes)
                if is_turning_machine or is_vtl_machine or is_milling_machine or is_5axis_machine:
                    machine_compatible_with_geometry = True
                # Prefer VTL for large diameter circular parts
                if is_vtl_machine and part_diameter > 500:
                    machine_score += 10  # Bonus for VTL on large parts
                    
            elif part_geometry in ["rectangular", "complex"]:
                # These typically need milling
                if is_milling_machine or is_5axis_machine:
                    machine_compatible_with_geometry = True
                elif is_turning_machine and not any(k in job_title + job_description for k in ["block", "plate", "housing", "bracket"]):
                    # Allow turning only if job doesn't specifically mention prismatic parts
                    machine_compatible_with_geometry = True
                else:
                    machine_rejection = f"Geometry '{part_geometry}' requires milling machine"
                    
            elif part_geometry == "sheet_metal":
                if is_press_machine or is_cutting_machine:
                    machine_compatible_with_geometry = True
                else:
                    machine_rejection = f"Sheet metal geometry requires press/cutting machine"
                    
            elif part_geometry == "spherical":
                if is_turning_machine or is_5axis_machine:
                    machine_compatible_with_geometry = True
                    
            else:
                # Unknown geometry - allow all machine types
                machine_compatible_with_geometry = True
            
            if not machine_compatible_with_geometry:
                if machine_rejection and machine_rejection not in rejection_reasons:
                    rejection_reasons.append(machine_rejection)
                continue
            
            geometry_compatible = True
            
            # ============== WEIGHT CAPACITY CHECK ==============
            machine_max_weight = machine.get("max_weight") or machine.get("table_load_capacity") or machine.get("max_load") or 0
            if part_weight > 0 and machine_max_weight > 0:
                if machine_max_weight >= part_weight * 1.2:  # 20% safety margin
                    weight_fit = True
                    weight_capable = True
                    machine_score += 5
                else:
                    weight_fit = False
                    machine_rejection = f"Weight {part_weight}kg exceeds machine capacity {machine_max_weight}kg"
                    if machine_rejection not in rejection_reasons:
                        rejection_reasons.append(machine_rejection)
                    continue
            
            # ============== DIMENSION CAPABILITY CHECK ==============
            # Check if machine envelope can fit the part based on machine category AND geometry
            
            if is_turning_machine or is_vtl_machine or "turning" in machine_category or "lathe" in machine_category or "vtl" in machine_category:
                # For lathes/VTLs: check max_diameter (swing) and max_length (between centers)
                machine_max_dia = machine.get("max_diameter") or machine.get("max_swing") or machine.get("swing_over_bed") or 0
                machine_max_len = machine.get("max_length") or machine.get("distance_between_centers") or 0
                machine_bore = machine.get("spindle_bore") or machine.get("bore_diameter") or 0
                
                # Check diameter capability
                check_diameter = part_diameter or part_large_diameter or 0
                if check_diameter > 0 and machine_max_dia > 0:
                    if machine_max_dia >= check_diameter * 1.1:  # 10% margin
                        dimension_fit = True
                        dimension_capable = True
                        machine_score += 15
                    else:
                        machine_rejection = f"Part diameter {check_diameter}mm exceeds machine swing {machine_max_dia}mm"
                        if machine_rejection not in rejection_reasons:
                            rejection_reasons.append(machine_rejection)
                        continue
                
                # Check length capability for cylindrical parts
                check_length = part_length or 0
                if check_length > 0 and machine_max_len > 0:
                    if machine_max_len >= check_length * 1.1:
                        dimension_fit = True
                        dimension_capable = True
                        machine_score += 10
                    else:
                        machine_rejection = f"Part length {check_length}mm exceeds machine capacity {machine_max_len}mm"
                        if machine_rejection not in rejection_reasons:
                            rejection_reasons.append(machine_rejection)
                        continue
                
                # Check bore through capacity for tube/pipe
                if part_geometry == "tube_pipe" and part_inner_diameter > 0:
                    if machine_bore > 0 and machine_bore >= part_inner_diameter:
                        machine_score += 5  # Bonus for bar work capability
                        dimension_fit = True
                        dimension_capable = True
                        machine_score += 10
                        
            elif is_milling_machine or is_5axis_machine or "milling" in machine_category or "vmc" in machine_category:
                # For milling machines: check X, Y, Z travels
                max_x = machine.get("max_x") or machine.get("table_size_x") or machine.get("x_travel") or 0
                max_y = machine.get("max_y") or machine.get("table_size_y") or machine.get("y_travel") or 0
                max_z = machine.get("max_z") or machine.get("z_travel") or 0
                table_load = machine.get("table_load_capacity") or machine.get("max_weight") or 0
                
                # Check all three axes
                dimension_issues = []
                if part_length and max_x and max_x < part_length * 1.1:
                    dimension_issues.append(f"X-travel {max_x}mm < part length {part_length}mm")
                if part_width and max_y and max_y < part_width * 1.1:
                    dimension_issues.append(f"Y-travel {max_y}mm < part width {part_width}mm")
                if part_height and max_z and max_z < part_height * 1.1:
                    dimension_issues.append(f"Z-travel {max_z}mm < part height {part_height}mm")
                
                if dimension_issues:
                    machine_rejection = f"Part exceeds machine envelope: {', '.join(dimension_issues)}"
                    if machine_rejection not in rejection_reasons:
                        rejection_reasons.append(machine_rejection)
                    continue
                
                # Part fits
                if max_x or max_y or max_z:
                    dimension_fit = True
                    dimension_capable = True
                    machine_score += 15
                    
                # Bonus for 5-axis capability on complex parts
                if is_5axis_machine and part_geometry == "complex":
                    machine_score += 10
                    
            elif is_boring_machine or "boring" in machine_category:
                # For boring machines: check bore diameter capability
                bore_dia = machine.get("bore_diameter") or machine.get("max_diameter") or 0
                if part_diameter and bore_dia > 0:
                    if bore_dia >= part_diameter * 1.1:
                        dimension_fit = True
                        dimension_capable = True
                        machine_score += 15
                        
            elif is_gear_machine or "gear" in machine_category:
                # For gear machines: check max gear diameter and module
                max_gear_dia = machine.get("max_diameter") or 0
                if part_diameter and max_gear_dia > 0:
                    if max_gear_dia >= part_diameter:
                        dimension_fit = True
                        dimension_capable = True
                        machine_score += 15
            else:
                # General envelope check
                max_x = machine.get("max_x") or 0
                max_y = machine.get("max_y") or 0
                max_z = machine.get("max_z") or 0
                max_dia = machine.get("max_diameter") or 0
                machine_max = max(max_x, max_y, max_z, max_dia)
                
                if max_dimension and machine_max >= max_dimension:
                    dimension_fit = True
                    dimension_capable = True
                    machine_score += 15
            
            # ============== PROCESS MATCHING ==============
            # Check if this machine can perform required processes
            all_processes = recommended_processes + detected_processes
            
            for process in all_processes:
                process_lower = process.lower() if isinstance(process, str) else ""
                
                # Milling processes
                if any(keyword in process_lower for keyword in ["milling", "mill", "face", "pocket", "profile", "slot"]):
                    if is_milling_machine or is_5axis_machine:
                        machine_process_match = True
                        if is_5axis_machine:
                            machine_score += 30
                            if "5-Axis Milling" not in process_matches:
                                process_matches.append("5-Axis Milling")
                        else:
                            machine_score += 25
                            if "CNC Milling" not in process_matches:
                                process_matches.append("CNC Milling")
                        break
                
                # Turning processes
                elif any(keyword in process_lower for keyword in ["turn", "lathe", "shaft", "spindle", "axle", "cylinder"]):
                    if is_turning_machine:
                        machine_process_match = True
                        machine_score += 25
                        if "CNC Turning" not in process_matches:
                            process_matches.append("CNC Turning")
                        break
                
                # Gear manufacturing
                elif any(keyword in process_lower for keyword in ["gear", "hobbing", "spline", "sprocket"]):
                    if is_gear_machine:
                        machine_process_match = True
                        machine_score += 25
                        if "Gear Manufacturing" not in process_matches:
                            process_matches.append("Gear Manufacturing")
                        break
                
                # Boring
                elif any(keyword in process_lower for keyword in ["boring", "bore", "ream"]):
                    if is_boring_machine or is_turning_machine:
                        machine_process_match = True
                        machine_score += 20
                        if "Boring" not in process_matches:
                            process_matches.append("Boring")
                        break
                
                # VTL specific
                elif any(keyword in process_lower for keyword in ["vtl", "vertical turret", "large diameter", "ring", "flange"]):
                    if "vtl" in machine_type_lower:
                        machine_process_match = True
                        machine_score += 25
                        if "VTL Turning" not in process_matches:
                            process_matches.append("VTL Turning")
                        break
                
                # Drilling/Tapping
                elif any(keyword in process_lower for keyword in ["drill", "tap", "thread", "hole"]):
                    if is_drilling_machine or is_milling_machine:
                        machine_process_match = True
                        machine_score += 15
                        if "Drilling/Tapping" not in process_matches:
                            process_matches.append("Drilling/Tapping")
                        break
                
                # Grinding
                elif any(keyword in process_lower for keyword in ["grind", "surface finish", "polish"]):
                    if is_grinding_machine:
                        machine_process_match = True
                        machine_score += 20
                        if "Grinding" not in process_matches:
                            process_matches.append("Grinding")
                        break
                
                # EDM
                elif any(keyword in process_lower for keyword in ["edm", "wire cut", "spark"]):
                    if is_edm_machine:
                        machine_process_match = True
                        machine_score += 20
                        if "EDM" not in process_matches:
                            process_matches.append("EDM")
                        break
                
                # Welding
                elif any(keyword in process_lower for keyword in ["weld", "fabricat", "join"]):
                    if is_welding_machine:
                        machine_process_match = True
                        machine_score += 25
                        if "Welding" not in process_matches:
                            process_matches.append("Welding")
                        break
                
                # Sheet Metal
                elif any(keyword in process_lower for keyword in ["sheet", "bend", "press", "punch", "brake"]):
                    if is_press_machine:
                        machine_process_match = True
                        machine_score += 20
                        if "Sheet Metal" not in process_matches:
                            process_matches.append("Sheet Metal")
                        break
                
                # Cutting
                elif any(keyword in process_lower for keyword in ["laser", "plasma", "waterjet", "cut"]):
                    if is_cutting_machine:
                        machine_process_match = True
                        machine_score += 20
                        if "Laser/Cutting" not in process_matches:
                            process_matches.append("Laser/Cutting")
                        break
            
            # SKIP this machine if it doesn't match any required process
            if not machine_process_match:
                continue
            
            has_suitable_machine = True
            
            # ============== TOLERANCE CHECK (+20 points) ==============
            machine_tolerance = machine.get("tolerance") or machine.get("tolerance_capability") or 1.0
            if machine_tolerance <= required_tolerance:
                tolerance_capable = True
                machine_score += 20
            
            # ============== MATERIAL CHECK (+15 points) ==============
            machine_materials = [m.lower() for m in (machine.get("materials_supported") or machine.get("materials") or [])]
            material_matched = False
            check_materials = [required_material, ai_material] if ai_material else [required_material]
            for check_mat in check_materials:
                if check_mat:
                    for mat in machine_materials:
                        if check_mat in mat or mat in check_mat:
                            material_matched = True
                            materials_match = True
                            machine_score += 15
                            break
                if material_matched:
                    break
            
            # ============== KEYWORD MATCHING BONUS (+10 points max) ==============
            machine_text = f"{machine_type_lower} {machine_category} {machine.get('brand', '')} {machine.get('model', '')}".lower()
            for keyword in detected_keywords:
                if keyword in machine_text and keyword not in keyword_matches:
                    keyword_matches.append(keyword)
                    machine_score += 2  # 2 points per keyword match
            
            # ============== AVAILABILITY BONUS FOR URGENT RFQS ==============
            if is_machine_available:
                available_machine_count += 1
                has_available_machine = True
                if is_urgent_rfq:
                    machine_score += 10  # Bonus for available machine on urgent RFQ
            
            total_matching_machines += 1
            
            matching_machines.append({
                "name": machine_name,
                "category": machine.get("machine_category", ""),
                "score": min(machine_score, 60),  # Cap individual machine score (increased for availability)
                "tolerance": machine_tolerance,
                "dimension_fit": dimension_fit,
                "weight_fit": weight_fit,
                "envelope": f"{machine.get('max_x', 0)}x{machine.get('max_y', 0)}x{machine.get('max_z', 0)}mm" if machine.get('max_x') else f"Ø{machine.get('max_diameter', 0)}x{machine.get('max_length', 0)}mm",
                "max_weight": machine_max_weight,
                "availability_status": machine_availability,
                "is_available": is_machine_available,
                "engaged_until": machine.get("engaged_until")
            })
        
        # Only include vendor if they have at least one suitable machine
        if has_suitable_machine and matching_machines:
            # Sort machines by score, prioritizing available machines for urgent RFQs
            if is_urgent_rfq:
                # For urgent RFQs, available machines get priority even with lower scores
                matching_machines.sort(key=lambda x: (x.get("is_available", False), x["score"]), reverse=True)
            else:
                matching_machines.sort(key=lambda x: x["score"], reverse=True)
            
            best_machine_score = matching_machines[0]["score"]
            
            # ============== CALCULATE FINAL SCORE ==============
            # Base score from best machine (max 60 - increased to accommodate availability)
            final_score = best_machine_score
            
            # Experience bonus (max 35 - increased weightage)
            final_score += experience_score
            
            # Geometry compatibility bonus
            if geometry_compatible:
                final_score += 5
            
            # Vendor rating bonus (max 10)
            vendor_rating = vendor.get("rating", 0)
            final_score += min(vendor_rating * 2, 10)
            
            # Total jobs bonus (max 10)
            total_jobs = vendor.get("total_jobs", 0)
            final_score += min(total_jobs / 10, 10)
            
            # Keyword matching bonus (max 10)
            final_score += min(len(keyword_matches) * 2, 10)
            
            # ============== AVAILABILITY SCORING FOR URGENT RFQS (max 20) ==============
            availability_score = 0
            availability_ratio = available_machine_count / total_matching_machines if total_matching_machines > 0 else 0
            
            if is_urgent_rfq:
                if has_available_machine:
                    # Base bonus for having at least one available machine
                    availability_score = 10
                    # Additional bonus based on ratio of available machines
                    availability_score += int(availability_ratio * 10)  # Up to 10 extra points
                else:
                    # Penalty for vendors without available machines on urgent RFQs
                    final_score = int(final_score * 0.8)  # 20% penalty
            elif rfq_urgency == "high":
                if has_available_machine:
                    availability_score = 5
                    availability_score += int(availability_ratio * 5)
            
            final_score += availability_score
            
            # ============== LOCATION PREFERENCE SCORING (max 15) ==============
            location_score = 0
            location_match_type = None
            vendor_country = (vendor.get("country") or "").lower().strip()
            vendor_city = (vendor.get("city") or "").lower().strip()
            
            # Get RFQ's preferred locations
            preferred_countries = [c.lower().strip() for c in (rfq.get("preferred_vendor_countries") or [])]
            preferred_cities = [c.lower().strip() for c in (rfq.get("preferred_vendor_cities") or [])]
            
            # City match takes priority (more specific = higher bonus)
            if preferred_cities and vendor_city:
                if vendor_city in preferred_cities:
                    location_score = 15  # Full bonus for exact city match
                    location_match_type = "city"
            
            # Country match (if no city match)
            if location_score == 0 and preferred_countries and vendor_country:
                if vendor_country in preferred_countries:
                    location_score = 10  # Country match bonus
                    location_match_type = "country"
            
            final_score += location_score
            
            # Cap at 100
            final_score = min(int(final_score), 100)
            
            matched_vendors.append({
                "vendor_id": vendor["vendor_id"],
                "user_id": vendor["user_id"],
                "company_name": vendor["company_name"],
                "suitability_score": final_score,
                "matching_machines": [m["name"] for m in matching_machines[:3]],
                "machine_details": matching_machines[:3],
                "materials_match": materials_match,
                "tolerance_capable": tolerance_capable,
                "dimension_capable": dimension_capable,
                "weight_capable": weight_capable,
                "geometry_compatible": geometry_compatible,
                "process_matches": list(set(process_matches))[:5],
                "keyword_matches": keyword_matches[:5],
                # Enhanced experience data
                "experience_score": experience_score,
                "similar_jobs_count": similar_jobs_count,
                "experience_keywords": experience_keywords_matched[:5],
                "has_profile_experience": len(vendor_past_experiences) > 0,
                "experience_details": experience_match_details[:3],  # Top 3 relevant experiences
                "best_experience_match": best_experience_match,  # Single best match
                "material_experience": material_experience,
                "process_experience": process_experience,
                "geometry_experience": geometry_experience,
                "part_type_experience": part_type_experience,
                # Location data
                "location": f"{vendor.get('city', '')}, {vendor.get('country', '')}",
                "location_match": location_match_type,
                "location_score": location_score,
                "rating": vendor.get("rating", 0),
                "total_jobs": vendor.get("total_jobs", 0),
                "certifications": vendor.get("certifications", [])[:3],
                "part_geometry": part_geometry,
                # NEW: Availability data for urgency
                "has_available_machine": has_available_machine,
                "available_machine_count": available_machine_count,
                "total_matching_machines": total_matching_machines,
                "availability_score": availability_score,
                "availability_ratio": round(availability_ratio, 2)
            })
    
    # Sort by score
    matched_vendors.sort(key=lambda x: x["suitability_score"], reverse=True)
    matched_vendors = matched_vendors[:10]  # Top 10
    
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {
            "matched_vendors": matched_vendors,
            "status": RFQStatus.MATCHING,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Send email notifications ONLY to vendors with 50%+ match score (non-blocking)
    app_url = os.environ.get("APP_URL", "https://rfq-marketplace-9.preview.emergentagent.com")
    buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "name": 1, "company_name": 1})
    buyer_name = buyer.get("name") or buyer.get("company_name", "Buyer") if buyer else "Buyer"
    
    qualified_vendors = [v for v in matched_vendors if v.get("suitability_score", 0) >= 50]
    
    # Send admin notification for vendor matching
    top_vendor = matched_vendors[0] if matched_vendors else {}
    asyncio.create_task(send_admin_notification("vendor_matching", {
        "rfq_id": rfq_id,
        "rfq_title": rfq.get("title", "Untitled"),
        "buyer_name": buyer_name,
        "matched_count": len(matched_vendors),
        "top_vendor": top_vendor.get("company_name", "N/A"),
        "top_score": top_vendor.get("suitability_score", 0)
    }))
    
    for matched in qualified_vendors:
        vendor_user = await db.users.find_one({"user_id": matched.get("user_id")}, {"_id": 0, "email": 1, "name": 1})
        if vendor_user and vendor_user.get("email"):
            email_data = {
                "vendor_name": vendor_user.get("name", "Vendor"),
                "rfq_title": rfq.get("title", "New RFQ"),
                "material": rfq.get("material_type", "N/A"),
                "quantity": rfq.get("quantity", "N/A"),
                "tolerance": rfq.get("tolerance", "N/A"),
                "buyer_name": buyer_name,
                "match_score": matched.get("suitability_score", 0),
                "matching_machines": ", ".join(matched.get("matching_machines", [])[:3]) or "Compatible machines found",
                "process_matches": ", ".join(matched.get("process_matches", [])[:3]) or "Matching capabilities",
                "app_url": f"{app_url}/vendor/matched-rfqs"
            }
            subject, html = get_email_template("vendor_matched", email_data)
            asyncio.create_task(send_email_async(vendor_user["email"], subject, html))
            
            # Create in-app notification
            await create_notification(
                user_id=matched.get("user_id"),
                notification_type=NotificationType.RFQ_MATCHED,
                title=f"New RFQ Match: {rfq.get('title', 'Untitled')[:40]}",
                message=f"You've been matched ({matched.get('suitability_score', 0)}%) to a new RFQ for {rfq.get('material_type', 'Unknown')} - {rfq.get('quantity', 1)} units",
                data={
                    "rfq_id": rfq_id,
                    "match_score": matched.get("suitability_score", 0),
                    "link": f"/vendor/rfq/{rfq_id}"
                }
            )
            
            # Send WhatsApp notification with friendly message
            vendor_profile = await db.vendors.find_one({"user_id": matched.get("user_id")}, {"_id": 0, "phone": 1, "company_name": 1})
            if vendor_profile and vendor_profile.get("phone") and whatsapp_service.is_configured():
                company_name = vendor_profile.get("company_name", "Partner")
                part_name = rfq.get("title", "New Part")[:50]
                
                # Get process from AI analysis
                ai_analysis = rfq.get("ai_analysis") or {}
                processes = ai_analysis.get("recommended_processes") or []
                process_str = ", ".join(processes[:2]) if processes else rfq.get("material_type", "Manufacturing")
                
                quantity_str = str(rfq.get("quantity", "As Required"))
                
                # Calculate deadline
                deadline_date = rfq.get("deadline")
                if deadline_date:
                    try:
                        if isinstance(deadline_date, str):
                            deadline_dt = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
                        else:
                            deadline_dt = deadline_date
                        deadline_str = deadline_dt.strftime("%d %b %Y")
                    except:
                        deadline_str = "As per RFQ"
                else:
                    deadline_str = "As per RFQ"
                
                # Get urgency emoji
                urgency = rfq.get("urgency", "normal")
                urgency_emoji = {"urgent": "🔴", "high": "🟠", "normal": "🟢", "low": "🔵"}.get(urgency, "🟢")
                
                # Generate magic link for instant access
                base_url = "https://oemlinker.com"
                magic_result = await generate_magic_link_for_user(matched.get("user_id"), f"/vendor/rfq/{rfq_id}")
                if magic_result.get("success"):
                    rfq_link = f"{base_url}/magic-login?token={magic_result['token']}"
                    link_note = "🔑 _Click for instant access (no login needed)_"
                else:
                    rfq_link = f"{base_url}/vendor/rfq/{rfq_id}"
                    link_note = "_Login to view and submit quote_"
                
                # User-friendly notification message
                notification_message = f"""🔔 *New RFQ Match for You!*

Hello *{company_name}*,

Great news! A new RFQ matching your capabilities is available.

📋 *{part_name}*
{urgency_emoji} Priority: {urgency.title()}
🔧 Process: {process_str}
📦 Quantity: {quantity_str}
📅 Deadline: {deadline_str}
🎯 Match Score: {matched.get('suitability_score', 0)}%

👉 *Submit your quote:*
{rfq_link}

{link_note}

Reply *rfqs* to see all opportunities.

_Team OEMLinker_"""

                # Send friendly text message
                asyncio.create_task(whatsapp_service.send_text_message(
                    vendor_profile["phone"], 
                    notification_message
                ))
                
                # Send drawing files if available (async task)
                drawing_ids = rfq.get("drawing_ids", [])
                if drawing_ids:
                    asyncio.create_task(send_rfq_drawings_to_vendor(
                        vendor_profile["phone"],
                        rfq_id,
                        drawing_ids,
                        part_name
                    ))
    
    return {
        "matched_vendors": matched_vendors, 
        "total_matches": len(matched_vendors),
        "vendors_notified": len(qualified_vendors),
        "notification_threshold": "50%",
        "dimensions_from_text": dimensions_from_text,
        "text_extracted_dimensions": text_dims if dimensions_from_text else None,
        # Urgency info
        "rfq_urgency": rfq_urgency,
        "urgency_applied": is_urgent_rfq,
        "availability_prioritized": is_urgent_rfq
    }

@api_router.post("/rfqs/{rfq_id}/submit")
async def submit_rfq(rfq_id: str, user: dict = Depends(get_current_user)):
    """Submit RFQ to matched vendors"""
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {"status": RFQStatus.SUBMITTED, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "RFQ submitted to vendors", "status": RFQStatus.SUBMITTED}


# ============== ENHANCED RFQ ANALYSIS & DISTRIBUTION ==============

@api_router.post("/rfq/analyze-and-match")
async def analyze_and_match_rfq(request: Request, user: dict = Depends(get_current_user)):
    """
    Analyze RFQ drawings using AI and match with suitable vendors.
    Supports multi-drawing RFQs with intelligent process detection.
    """
    body = await request.json()
    rfq_id = body.get("rfq_id")
    
    if not rfq_id:
        raise HTTPException(status_code=400, detail="rfq_id is required")
    
    # Get RFQ
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Verify ownership or admin access
    is_owner = rfq.get("buyer_id") == user["user_id"]
    is_admin = has_admin_access(user)
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get drawings for this RFQ
    drawings = await db.drawings.find({"rfq_id": rfq_id}, {"_id": 0, "file_data": 0}).to_list(20)
    
    # Analyze RFQ and update AI analysis
    ai_analysis = rfq.get("ai_analysis") or {}
    
    # Detect process requirements based on AI analysis and RFQ data
    process_detection = detect_process_requirements(rfq, ai_analysis)
    
    # Update RFQ with process detection
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {
            "process_detected": process_detection["primary_process"],
            "processes_required": process_detection["all_processes"],
            "raw_material_provided": process_detection["raw_material_provided"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Get all approved vendors
    vendors = await db.vendors.find({"is_approved": True}, {"_id": 0}).to_list(200)
    
    # Match vendors based on process requirements
    matched_vendors = []
    rejected_vendors = []
    
    for vendor in vendors:
        # Get vendor machines
        machines = await db.machines.find(
            {"vendor_id": vendor["vendor_id"], "is_active": True}, 
            {"_id": 0}
        ).to_list(50)
        
        vendor_categories = list(set(m.get("machine_category", "") for m in machines))
        
        # Determine if vendor matches the process requirements
        match_result = evaluate_vendor_match(
            vendor, 
            machines, 
            vendor_categories,
            process_detection,
            rfq
        )
        
        if match_result["is_match"]:
            matched_vendors.append({
                "vendor_id": vendor["vendor_id"],
                "company_name": vendor.get("company_name", "Unknown"),
                "city": vendor.get("city", ""),
                "state": vendor.get("state", ""),
                "suitability_score": match_result["score"],
                "matched_capabilities": match_result["capabilities"],
                "match_reason": match_result["reason"],
                "match_type": "auto"
            })
        else:
            rejected_vendors.append({
                "vendor_id": vendor["vendor_id"],
                "company_name": vendor.get("company_name", "Unknown"),
                "rejection_reason": match_result["rejection_reason"]
            })
    
    # Sort by score
    matched_vendors.sort(key=lambda x: x["suitability_score"], reverse=True)
    
    # Update RFQ with matched vendors
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {
            "matched_vendors": matched_vendors[:20],  # Top 20 matches
            "status": RFQStatus.MATCHING if matched_vendors else rfq.get("status"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Log activity
    activity_log = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "type": "rfq_analyzed",
        "action": "analyze_and_match",
        "entity_type": "rfq",
        "entity_id": rfq_id,
        "user_id": user["user_id"],
        "details": {
            "rfq_title": rfq.get("title"),
            "process_detected": process_detection["primary_process"],
            "vendors_matched": len(matched_vendors),
            "vendors_rejected": len(rejected_vendors)
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activity_logs.insert_one(activity_log)
    
    return {
        "rfq_id": rfq_id,
        "process_detection": process_detection,
        "matched_vendors": matched_vendors,
        "rejected_vendors": rejected_vendors[:10],  # First 10 rejections
        "total_matched": len(matched_vendors),
        "total_rejected": len(rejected_vendors)
    }


def detect_process_requirements(rfq: dict, ai_analysis: dict) -> dict:
    """
    Detect required processes based on RFQ data and AI analysis.
    Returns process type and whether raw material is provided.
    """
    # Keywords for different processes
    casting_keywords = ["casting", "cast", "foundry", "sand cast", "die cast", "investment cast", "mould", "molten"]
    forging_keywords = ["forging", "forge", "forged", "hot working", "drop forge", "press forge"]
    machining_keywords = ["machining", "cnc", "turning", "milling", "drilling", "boring", "grinding", "lathe", "vmc", "hmc"]
    fabrication_keywords = ["fabrication", "welding", "sheet metal", "laser cut", "plasma", "bending", "rolling"]
    
    # Check supply type
    supply_type = rfq.get("supply_type", "vendor_material")
    raw_material_provided = supply_type == "buyer_material"
    
    # Combine all text for keyword matching
    text = f"{rfq.get('title', '')} {rfq.get('description', '')} {rfq.get('material_type', '')}".lower()
    
    # Also check AI recommended processes
    recommended_processes = ai_analysis.get("recommended_processes", [])
    ai_text = " ".join(recommended_processes).lower()
    combined_text = f"{text} {ai_text}"
    
    # Detect processes
    processes = []
    primary_process = "machining"  # Default
    
    if any(kw in combined_text for kw in casting_keywords):
        processes.append("casting")
        primary_process = "casting"
    
    if any(kw in combined_text for kw in forging_keywords):
        processes.append("forging")
        if "casting" not in processes:
            primary_process = "forging"
    
    if any(kw in combined_text for kw in fabrication_keywords):
        processes.append("fabrication")
        if not processes:
            primary_process = "fabrication"
    
    if any(kw in combined_text for kw in machining_keywords) or raw_material_provided:
        processes.append("machining")
        # If raw material is provided, machining is primary
        if raw_material_provided:
            primary_process = "machining"
    
    # If no process detected, default to machining
    if not processes:
        processes = ["machining"]
    
    # If raw material is provided, exclude casting and forging
    if raw_material_provided:
        processes = [p for p in processes if p not in ["casting", "forging"]]
        if not processes:
            processes = ["machining"]
        primary_process = "machining"
    
    return {
        "primary_process": primary_process,
        "all_processes": processes,
        "raw_material_provided": raw_material_provided,
        "material_type": rfq.get("material_type"),
        "notes": f"Detected from RFQ analysis. Supply type: {supply_type}"
    }


def evaluate_vendor_match(vendor: dict, machines: list, vendor_categories: list, process_detection: dict, rfq: dict) -> dict:
    """
    Evaluate if a vendor matches the RFQ requirements.
    """
    primary_process = process_detection["primary_process"]
    all_processes = process_detection["all_processes"]
    raw_material_provided = process_detection["raw_material_provided"]
    
    # Map processes to required machine categories
    process_to_categories = {
        "casting": ["Casting"],
        "forging": ["Forging"],
        "machining": ["CNC Turning/Lathe", "VMC (Vertical Machining Center)", "HMC (Horizontal Machining Center)", 
                     "5-Axis Machining", "Milling", "Grinding", "Boring", "Drilling", "VTL (Vertical Turret Lathe)"],
        "fabrication": ["Sheet Metal", "Welding", "Laser Cutting"]
    }
    
    # Check if vendor has capability for required processes
    required_categories = []
    for proc in all_processes:
        required_categories.extend(process_to_categories.get(proc, []))
    
    # Find matching capabilities
    matched_capabilities = []
    for cat in vendor_categories:
        if cat in required_categories or any(req.lower() in cat.lower() for req in required_categories):
            matched_capabilities.append(cat)
    
    # If raw material is provided, only match machining vendors
    if raw_material_provided:
        if any(cat in process_to_categories["casting"] for cat in vendor_categories):
            # Vendor is casting-focused, not suitable for machining-only jobs
            if not matched_capabilities:
                return {
                    "is_match": False,
                    "score": 0,
                    "capabilities": [],
                    "reason": "",
                    "rejection_reason": "Raw material provided - only machining vendors needed, vendor is casting-focused"
                }
        if any(cat in process_to_categories["forging"] for cat in vendor_categories):
            if not matched_capabilities:
                return {
                    "is_match": False,
                    "score": 0,
                    "capabilities": [],
                    "reason": "",
                    "rejection_reason": "Raw material provided - only machining vendors needed, vendor is forging-focused"
                }
    
    # No matching capabilities
    if not matched_capabilities:
        return {
            "is_match": False,
            "score": 0,
            "capabilities": [],
            "reason": "",
            "rejection_reason": f"No matching capabilities for {primary_process}"
        }
    
    # Calculate score
    score = 50  # Base score
    
    # Bonus for multiple matching capabilities
    score += len(matched_capabilities) * 10
    
    # Cap at 100
    score = min(score, 100)
    
    return {
        "is_match": True,
        "score": score,
        "capabilities": matched_capabilities[:5],
        "reason": f"Matched for {primary_process}: {', '.join(matched_capabilities[:3])}",
        "rejection_reason": None
    }


@api_router.get("/rfq/{rfq_id}/vendors")
async def get_rfq_matched_vendors(rfq_id: str, user: dict = Depends(get_current_user)):
    """Get all vendors matched to an RFQ with their status"""
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Verify ownership or admin access
    is_owner = rfq.get("buyer_id") == user["user_id"]
    is_admin = has_admin_access(user)
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    matched_vendors = rfq.get("matched_vendors", [])
    
    # Enrich with quote status
    for mv in matched_vendors:
        quote = await db.quotes.find_one(
            {"rfq_id": rfq_id, "vendor_id": mv["vendor_id"]},
            {"_id": 0, "quote_id": 1, "total_cost": 1, "status": 1}
        )
        mv["has_quoted"] = quote is not None
        mv["quote_info"] = {
            "quote_id": quote.get("quote_id"),
            "total_cost": quote.get("total_cost"),
            "status": quote.get("status")
        } if quote else None
    
    return {
        "rfq_id": rfq_id,
        "process_detected": rfq.get("process_detected"),
        "raw_material_provided": rfq.get("raw_material_provided", False),
        "matched_vendors": matched_vendors,
        "total_matched": len(matched_vendors)
    }


@api_router.get("/rfq/{rfq_id}/quotations")
async def get_rfq_quotations(rfq_id: str, user: dict = Depends(get_current_user)):
    """Get all quotations for an RFQ with cost breakdown comparison.
    Supports both flat and item-wise quotations."""
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Verify ownership or admin access
    is_owner = rfq.get("buyer_id") == user["user_id"]
    is_admin = has_admin_access(user)
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all quotes for this RFQ
    quotes = await db.quotes.find({"rfq_id": rfq_id}, {"_id": 0}).to_list(50)
    
    # Enrich with vendor info
    quotations = []
    has_itemwise_quotes = False
    
    for quote in quotes:
        vendor = await db.vendors.find_one(
            {"vendor_id": quote["vendor_id"]},
            {"_id": 0, "company_name": 1, "city": 1, "state": 1, "rating": 1}
        )
        
        is_itemwise = quote.get("is_itemwise", False)
        if is_itemwise:
            has_itemwise_quotes = True
        
        # Calculate totals for item-wise quotes
        if is_itemwise and quote.get("items"):
            total_material = sum(item.get("material_cost", 0) for item in quote["items"])
            total_labour = sum(item.get("labour_cost", 0) for item in quote["items"])
            total_additional = sum(
                sum(item.get("additional_costs", {}).values()) 
                for item in quote["items"]
            )
        else:
            total_material = quote.get("material_cost", 0)
            total_labour = quote.get("machining_cost", 0)
            total_additional = sum(quote.get("additional_costs", {}).values()) if quote.get("additional_costs") else 0
        
        quotation_data = {
            "quote_id": quote.get("quote_id"),
            "vendor_id": quote.get("vendor_id"),
            "vendor_name": vendor.get("company_name", "Unknown") if vendor else "Unknown",
            "vendor_location": f"{vendor.get('city', '')}, {vendor.get('state', '')}" if vendor else "",
            "vendor_rating": vendor.get("rating", 0) if vendor else 0,
            "is_itemwise": is_itemwise,
            "items": quote.get("items", []) if is_itemwise else [],
            "items_count": len(quote.get("items", [])) if is_itemwise else 0,
            # Partial quote fields
            "is_partial": quote.get("is_partial", False),
            "quoted_items_count": quote.get("quoted_items_count", len(quote.get("items", [])) if is_itemwise else 1),
            "total_rfq_items": quote.get("total_rfq_items", 1),
            "quoted_item_ids": quote.get("quoted_item_ids", []),
            "material_provided_by_buyer": quote.get("material_provided_by_buyer", False),
            "material_cost": total_material,
            "machining_cost": total_labour,
            "labour_cost": total_labour,  # Alias for clarity
            "additional_costs": quote.get("additional_costs", {}),
            "additional_costs_total": total_additional,
            "total_cost": quote.get("total_cost") or quote.get("price", 0),
            "lead_time_days": quote.get("lead_time_days"),
            "currency": quote.get("currency", "INR"),
            "notes": quote.get("notes"),
            "cost_breakdown_remarks": quote.get("cost_breakdown_remarks"),
            "status": quote.get("status"),
            "is_selected": quote.get("is_selected", False),
            "created_at": quote.get("created_at")
        }
        quotations.append(quotation_data)
    
    # Sort by total cost
    quotations.sort(key=lambda x: x["total_cost"])
    
    # Find lowest costs
    lowest_total = min([q["total_cost"] for q in quotations]) if quotations else 0
    lowest_machining = min([q["machining_cost"] for q in quotations]) if quotations else 0
    
    # Count partial quotes
    partial_quotes = len([q for q in quotations if q.get("is_partial", False)])
    full_quotes = len([q for q in quotations if not q.get("is_partial", False)])
    
    return {
        "rfq_id": rfq_id,
        "rfq_title": rfq.get("title"),
        "quotations": quotations,
        "total_quotes": len(quotations),
        "has_itemwise_quotes": has_itemwise_quotes,
        "comparison_summary": {
            "lowest_total_cost": lowest_total,
            "lowest_machining_cost": lowest_machining,
            "average_total_cost": sum(q["total_cost"] for q in quotations) / len(quotations) if quotations else 0,
            "quotes_with_material": len([q for q in quotations if not q["material_provided_by_buyer"]]),
            "quotes_without_material": len([q for q in quotations if q["material_provided_by_buyer"]]),
            "itemwise_quotes": len([q for q in quotations if q["is_itemwise"]]),
            "flat_quotes": len([q for q in quotations if not q["is_itemwise"]]),
            "partial_quotes": partial_quotes,
            "full_quotes": full_quotes
        }
    }


@api_router.post("/vendor/quotation")
async def submit_vendor_quotation(request: Request, user: dict = Depends(get_current_user)):
    """
    Submit a quotation with detailed cost breakdown.
    Vendors can specify material, machining, and additional costs separately.
    """
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor profile required")
    
    body = await request.json()
    rfq_id = body.get("rfq_id")
    
    if not rfq_id:
        raise HTTPException(status_code=400, detail="rfq_id is required")
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Check if vendor already quoted
    existing_quote = await db.quotes.find_one({
        "rfq_id": rfq_id,
        "vendor_id": vendor["vendor_id"]
    })
    if existing_quote:
        raise HTTPException(status_code=400, detail="You have already submitted a quotation for this RFQ")
    
    # Extract quotation details
    material_provided_by_buyer = body.get("material_provided_by_buyer", False)
    material_cost = float(body.get("material_cost", 0)) if not material_provided_by_buyer else 0
    machining_cost = float(body.get("machining_cost", 0))
    additional_costs = body.get("additional_costs", {})
    
    # Validate machining cost
    if machining_cost <= 0:
        raise HTTPException(status_code=400, detail="Machining cost is required and must be greater than 0")
    
    # Validate material cost if buyer not providing
    if not material_provided_by_buyer and material_cost <= 0:
        raise HTTPException(status_code=400, detail="Material cost is required when vendor provides material")
    
    # Calculate total
    additional_costs_total = sum(float(v) for v in additional_costs.values()) if additional_costs else 0
    total_cost = material_cost + machining_cost + additional_costs_total
    
    quote_id = f"quote_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    quote_doc = {
        "quote_id": quote_id,
        "rfq_id": rfq_id,
        "vendor_id": vendor["vendor_id"],
        "price": total_cost,  # Legacy field
        "total_price": total_cost,
        "currency": body.get("currency", "INR"),
        "lead_time_days": int(body.get("lead_time_days", 7)),
        "notes": body.get("notes"),
        "proposed_payment_terms": body.get("proposed_payment_terms", "net_30"),
        "payment_terms_notes": body.get("payment_terms_notes"),
        "is_selected": False,
        "status": "pending",
        # Enhanced fields
        "material_provided_by_buyer": material_provided_by_buyer,
        "material_cost": material_cost,
        "machining_cost": machining_cost,
        "additional_costs": additional_costs,
        "total_cost": total_cost,
        "cost_breakdown_remarks": body.get("cost_breakdown_remarks"),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=14)).isoformat()
    }
    
    await db.quotes.insert_one(quote_doc)
    
    # Update RFQ status
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {"status": RFQStatus.QUOTED, "updated_at": now.isoformat()}}
    )
    
    # Notify buyer
    buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "email": 1, "name": 1})
    if buyer and buyer.get("email"):
        email_data = {
            "buyer_name": buyer.get("name", "Buyer"),
            "rfq_title": rfq.get("title", "Your RFQ"),
            "vendor_name": vendor.get("company_name", "Vendor"),
            "price": f"{total_cost:.2f}",
            "lead_time": body.get("lead_time_days", 7),
            "app_url": f"https://oemlinker.com/buyer/rfq/{rfq_id}"
        }
        subject, html = get_email_template("quote_received", email_data)
        asyncio.create_task(send_email_async(buyer["email"], subject, html))
    
    # Create in-app notification
    await create_notification(
        user_id=rfq["buyer_id"],
        notification_type=NotificationType.QUOTE_RECEIVED,
        title=f"New Quote from {vendor.get('company_name', 'Vendor')}",
        message=f"₹{total_cost:,.2f} for {rfq.get('title', 'your RFQ')[:30]} - {body.get('lead_time_days', 7)} days",
        data={
            "rfq_id": rfq_id,
            "quote_id": quote_id,
            "vendor_name": vendor.get("company_name"),
            "total_cost": total_cost,
            "material_cost": material_cost,
            "machining_cost": machining_cost,
            "link": f"/buyer/rfq/{rfq_id}"
        }
    )
    
    logger.info(f"Quotation submitted: {quote_id} for RFQ {rfq_id} by vendor {vendor['vendor_id']}")
    
    return {
        "success": True,
        "quote_id": quote_id,
        "total_cost": total_cost,
        "cost_breakdown": {
            "material_cost": material_cost,
            "machining_cost": machining_cost,
            "additional_costs": additional_costs,
            "additional_costs_total": additional_costs_total
        },
        "message": "Quotation submitted successfully"
    }


@api_router.post("/vendor/quotation/itemwise")
async def submit_itemwise_quotation(request: Request, user: dict = Depends(get_current_user)):
    """
    Submit an item-wise quotation for RFQs with multiple drawings.
    Each drawing/item gets its own cost breakdown.
    """
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor profile required")
    
    body = await request.json()
    rfq_id = body.get("rfq_id")
    items = body.get("items", [])
    
    if not rfq_id:
        raise HTTPException(status_code=400, detail="rfq_id is required")
    
    if not items or len(items) == 0:
        raise HTTPException(status_code=400, detail="At least one item quotation is required")
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Check if vendor already quoted
    existing_quote = await db.quotes.find_one({
        "rfq_id": rfq_id,
        "vendor_id": vendor["vendor_id"]
    })
    if existing_quote:
        raise HTTPException(status_code=400, detail="You have already submitted a quotation for this RFQ")
    
    # Process and validate each item
    processed_items = []
    grand_total = 0
    
    for item in items:
        item_id = item.get("item_id") or item.get("drawing_id")
        if not item_id:
            raise HTTPException(status_code=400, detail="Each item must have an item_id or drawing_id")
        
        material_provided_by_buyer = item.get("material_provided_by_buyer", False)
        material_cost = float(item.get("material_cost", 0)) if not material_provided_by_buyer else 0
        labour_cost = float(item.get("labour_cost", 0))
        additional_costs = item.get("additional_costs", {})
        
        # Validate labour cost
        if labour_cost <= 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Labour/machining cost is required for item {item.get('title', item_id)}"
            )
        
        # Validate material cost if vendor provides material
        if not material_provided_by_buyer and material_cost <= 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Material cost is required for item {item.get('title', item_id)} when vendor provides material"
            )
        
        # Calculate item total
        additional_total = sum(float(v) for v in additional_costs.values()) if additional_costs else 0
        item_total = material_cost + labour_cost + additional_total
        grand_total += item_total
        
        processed_items.append({
            "item_id": item_id,
            "drawing_id": item.get("drawing_id"),
            "title": item.get("title", ""),
            "material_provided_by_buyer": material_provided_by_buyer,
            "material_cost": material_cost,
            "labour_cost": labour_cost,
            "additional_costs": additional_costs,
            "total_cost": item_total,
            "remarks": item.get("remarks", "")
        })
    
    quote_id = f"quote_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Get total RFQ items count to determine if this is a partial quote
    drawings = await db.drawings.find({"rfq_id": rfq_id}, {"_id": 0}).to_list(100)
    total_rfq_items = len(drawings) if drawings else 1
    quoted_items_count = len(processed_items)
    is_partial = quoted_items_count < total_rfq_items
    
    # Get item IDs that were quoted
    quoted_item_ids = [item["item_id"] for item in processed_items]
    
    quote_doc = {
        "quote_id": quote_id,
        "rfq_id": rfq_id,
        "vendor_id": vendor["vendor_id"],
        "price": grand_total,  # Legacy field
        "total_price": grand_total,
        "currency": body.get("currency", "INR"),
        "lead_time_days": int(body.get("lead_time_days", 7)),
        "notes": body.get("notes"),
        "proposed_payment_terms": body.get("proposed_payment_terms", "net_30"),
        "payment_terms_notes": body.get("payment_terms_notes"),
        "is_selected": False,
        "status": "pending",
        # Item-wise fields
        "is_itemwise": True,
        "items": processed_items,
        "total_cost": grand_total,
        "cost_breakdown_remarks": body.get("cost_breakdown_remarks"),
        # Partial quote fields
        "is_partial": is_partial,
        "quoted_items_count": quoted_items_count,
        "total_rfq_items": total_rfq_items,
        "quoted_item_ids": quoted_item_ids,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=14)).isoformat()
    }
    
    await db.quotes.insert_one(quote_doc)
    
    # Update RFQ status
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$set": {"status": RFQStatus.QUOTED, "updated_at": now.isoformat()}}
    )
    
    # Notify buyer
    buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "email": 1, "name": 1})
    if buyer and buyer.get("email"):
        email_data = {
            "buyer_name": buyer.get("name", "Buyer"),
            "rfq_title": rfq.get("title", "Your RFQ"),
            "vendor_name": vendor.get("company_name", "Vendor"),
            "price": f"{grand_total:.2f}",
            "lead_time": body.get("lead_time_days", 7),
            "app_url": f"https://oemlinker.com/buyer/rfq/{rfq_id}"
        }
        subject, html = get_email_template("quote_received", email_data)
        asyncio.create_task(send_email_async(buyer["email"], subject, html))
    
    # Create in-app notification
    quote_type = "Partial" if is_partial else "Item-wise"
    await create_notification(
        user_id=rfq["buyer_id"],
        notification_type=NotificationType.QUOTE_RECEIVED,
        title=f"{quote_type} Quote from {vendor.get('company_name', 'Vendor')}",
        message=f"₹{grand_total:,.2f} for {quoted_items_count}/{total_rfq_items} items in {rfq.get('title', 'your RFQ')[:30]}",
        data={
            "rfq_id": rfq_id,
            "quote_id": quote_id,
            "vendor_name": vendor.get("company_name"),
            "total_cost": grand_total,
            "items_count": quoted_items_count,
            "total_rfq_items": total_rfq_items,
            "is_partial": is_partial,
            "link": f"/buyer/rfq/{rfq_id}"
        }
    )
    
    logger.info(f"{'Partial' if is_partial else 'Full'} item-wise quotation submitted: {quote_id} for RFQ {rfq_id} with {quoted_items_count}/{total_rfq_items} items")
    
    return {
        "success": True,
        "quote_id": quote_id,
        "total_cost": grand_total,
        "items_count": quoted_items_count,
        "total_rfq_items": total_rfq_items,
        "is_partial": is_partial,
        "items": processed_items,
        "message": "Item-wise quotation submitted successfully"
    }


@api_router.get("/rfqs/{rfq_id}/items")
async def get_rfq_items_for_quoting(rfq_id: str, user: dict = Depends(get_current_user)):
    """
    Get RFQ drawings/items for vendor quoting.
    Returns each drawing as an item with details for quotation.
    """
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get all drawings for this RFQ
    drawings = await db.drawings.find(
        {"rfq_id": rfq_id},
        {"_id": 0}
    ).to_list(100)
    
    items = []
    for idx, drawing in enumerate(drawings, 1):
        # Get presigned URL for drawing
        drawing_url = None
        if drawing.get("s3_path"):
            from app.services.s3_storage_service import get_presigned_url
            drawing_url = get_presigned_url(drawing["s3_path"], expiration=3600)
        
        item = {
            "item_id": drawing.get("drawing_id"),
            "drawing_id": drawing.get("drawing_id"),
            "item_number": idx,
            "title": drawing.get("filename") or f"Item {idx}",
            "filename": drawing.get("filename"),
            "file_type": drawing.get("file_type"),
            "drawing_url": drawing_url,
            "material_type": rfq.get("material_type"),
            "quantity": rfq.get("quantity", 1),
            "tolerance": rfq.get("tolerance"),
            "ai_analysis": drawing.get("ai_analysis"),
            "raw_material_provided": rfq.get("supply_type") == "buyer_material"
        }
        items.append(item)
    
    # If no drawings, create a single item from RFQ itself
    if not items:
        items.append({
            "item_id": f"{rfq_id}_main",
            "drawing_id": None,
            "item_number": 1,
            "title": rfq.get("title", "Main Item"),
            "filename": None,
            "file_type": None,
            "drawing_url": None,
            "material_type": rfq.get("material_type"),
            "quantity": rfq.get("quantity", 1),
            "tolerance": rfq.get("tolerance"),
            "ai_analysis": rfq.get("ai_analysis"),
            "raw_material_provided": rfq.get("supply_type") == "buyer_material"
        })
    
    return {
        "rfq_id": rfq_id,
        "rfq_title": rfq.get("title"),
        "total_items": len(items),
        "items": items,
        "supply_type": rfq.get("supply_type", "vendor_material"),
        "raw_material_provided": rfq.get("supply_type") == "buyer_material"
    }


# ============== QUOTE ROUTES ==============

@api_router.get("/payment-terms")
async def get_payment_terms():
    """Get available payment terms options"""
    return {
        "terms": [
            {"value": k, "label": v} for k, v in PAYMENT_TERMS_LABELS.items()
        ]
    }

@api_router.post("/quotes", response_model=Quote)
async def create_quote(quote: QuoteCreate, user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor profile required")
    
    rfq = await db.rfqs.find_one({"rfq_id": quote.rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    quote_id = f"quote_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Calculate total cost from breakdown
    material_cost = quote.material_cost or 0 if not quote.material_provided_by_buyer else 0
    machining_cost = quote.machining_cost or 0
    additional_costs = quote.additional_costs or {}
    additional_costs_total = sum(additional_costs.values()) if additional_costs else 0
    total_cost = material_cost + machining_cost + additional_costs_total
    
    # Use total_cost as price for backward compatibility
    final_price = quote.price if quote.price > 0 else total_cost
    
    quote_doc = {
        "quote_id": quote_id,
        "rfq_id": quote.rfq_id,
        "vendor_id": vendor["vendor_id"],
        "price": final_price,  # Legacy field
        "total_price": total_cost,  # New calculated total
        "currency": quote.currency,
        "lead_time_days": quote.lead_time_days,
        "notes": quote.notes,
        "proposed_payment_terms": quote.proposed_payment_terms or "net_30",
        "payment_terms_notes": quote.payment_terms_notes,
        "is_selected": False,
        "status": "pending",
        # Enhanced quotation fields
        "material_provided_by_buyer": quote.material_provided_by_buyer,
        "material_cost": material_cost,
        "machining_cost": machining_cost,
        "additional_costs": additional_costs,
        "total_cost": total_cost,
        "cost_breakdown_remarks": quote.cost_breakdown_remarks,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=14)).isoformat()
    }
    
    await db.quotes.insert_one(quote_doc)
    
    # Update RFQ status
    await db.rfqs.update_one(
        {"rfq_id": quote.rfq_id},
        {"$set": {"status": RFQStatus.QUOTED, "updated_at": now.isoformat()}}
    )
    
    # Send email notification to buyer
    app_url = os.environ.get("APP_URL", "https://rfq-marketplace-9.preview.emergentagent.com")
    buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "email": 1, "name": 1})
    if buyer and buyer.get("email"):
        email_data = {
            "buyer_name": buyer.get("name", "Buyer"),
            "rfq_title": rfq.get("title", "Your RFQ"),
            "vendor_name": vendor.get("company_name", "Vendor"),
            "price": f"{quote.price:.2f}",
            "lead_time": quote.lead_time_days,
            "app_url": f"{app_url}/buyer/rfq/{quote.rfq_id}"
        }
        subject, html = get_email_template("quote_received", email_data)
        asyncio.create_task(send_email_async(buyer["email"], subject, html))
    
    # Create in-app notification for buyer
    await create_notification(
        user_id=rfq["buyer_id"],
        notification_type=NotificationType.QUOTE_RECEIVED,
        title=f"New Quote from {vendor.get('company_name', 'Vendor')}",
        message=f"${quote.price:,.2f} for {rfq.get('title', 'your RFQ')[:30]} - {quote.lead_time_days} days lead time",
        data={
            "rfq_id": quote.rfq_id,
            "quote_id": quote_id,
            "vendor_name": vendor.get("company_name"),
            "price": quote.price,
            "link": f"/buyer/rfq/{quote.rfq_id}"
        }
    )
    
    # Send admin notification for new quotation
    asyncio.create_task(send_admin_notification("new_quotation", {
        "quote_id": quote_id,
        "rfq_title": rfq.get("title", "Untitled"),
        "vendor_name": vendor.get("company_name", "Unknown"),
        "buyer_name": buyer.get("name", "Unknown") if buyer else "Unknown",
        "total_amount": quote.price,
        "lead_time": quote.lead_time_days
    }))
    
    # Send WhatsApp notification to buyer about new quote
    if buyer and whatsapp_service.is_configured():
        buyer_profile = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "phone": 1})
        if buyer_profile and buyer_profile.get("phone"):
            # Generate magic link for buyer
            magic_result = await generate_magic_link_for_user(rfq["buyer_id"], f"/buyer/rfq/{quote.rfq_id}")
            if magic_result.get("success"):
                review_link = f"https://oemlinker.com/magic-login?token={magic_result['token']}"
                link_note = "🔑 _Click for instant access_"
            else:
                review_link = f"https://oemlinker.com/buyer/rfq/{quote.rfq_id}"
                link_note = ""
            
            wa_message = f"""💰 *New Quote Received!*

📋 *{rfq.get('title', 'Your RFQ')}*

🏭 Vendor: {vendor.get('company_name', 'Vendor')}
💵 Price: ₹{quote.price:,.2f}
📅 Lead Time: {quote.lead_time_days} days
⭐ Vendor Rating: {vendor.get('rating', 0):.1f}/5

🔗 Review Quote:
{review_link}
{link_note}"""
            asyncio.create_task(whatsapp_service.send_text_message(buyer_profile["phone"], wa_message))
    
    return Quote(**quote_doc)

@api_router.get("/quotes/rfq/{rfq_id}")
async def get_quotes_for_rfq(rfq_id: str, user: dict = Depends(get_current_user)):
    quotes = await db.quotes.find({"rfq_id": rfq_id}, {"_id": 0}).to_list(50)
    
    # Enrich with detailed vendor info for comparison
    for quote in quotes:
        vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0})
        if vendor:
            quote["vendor_name"] = vendor.get("company_name", "Unknown")
            quote["vendor_rating"] = vendor.get("rating", 0)
            quote["vendor_total_jobs"] = vendor.get("total_jobs", 0)
            quote["vendor_location"] = f"{vendor.get('city', '')}, {vendor.get('country', '')}".strip(", ")
            quote["vendor_certifications"] = vendor.get("certifications", [])[:3]
            quote["vendor_id_ref"] = vendor.get("vendor_id")
            quote["vendor_user_id"] = vendor.get("user_id")
            
            # Get vendor's machines for capability info
            machines = await db.machines.find(
                {"vendor_id": vendor["vendor_id"], "is_active": True},
                {"_id": 0, "machine_type": 1, "machine_category": 1, "brand": 1}
            ).to_list(5)
            quote["vendor_machines"] = [
                f"{m.get('machine_type', '')} - {m.get('brand', '')}" 
                for m in machines
            ]
            
            # Get vendor's quote stats
            total_quotes = await db.quotes.count_documents({"vendor_id": vendor["vendor_id"]})
            accepted_quotes = await db.quotes.count_documents({"vendor_id": vendor["vendor_id"], "status": "accepted"})
            quote["vendor_acceptance_rate"] = round((accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0, 1)
    
    return quotes

@api_router.get("/quotes/vendor")
async def get_vendor_quotes(user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        return []
    
    quotes = await db.quotes.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).to_list(100)
    return quotes

@api_router.get("/quotes/{quote_id}")
async def get_quote_detail(quote_id: str, user: dict = Depends(get_current_user)):
    """Get detailed quote information for buyers"""
    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Get RFQ to verify access
    rfq = await db.rfqs.find_one({"rfq_id": quote["rfq_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Check authorization - buyer of RFQ or vendor who submitted the quote
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    is_buyer = rfq["buyer_id"] == user["user_id"]
    is_vendor = vendor and vendor["vendor_id"] == quote["vendor_id"]
    
    if not is_buyer and not is_vendor and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this quote")
    
    # Enrich with vendor details
    quote_vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0})
    if quote_vendor:
        quote["vendor_name"] = quote_vendor.get("company_name", "Unknown")
        quote["vendor_rating"] = quote_vendor.get("rating", 0)
        quote["vendor_total_jobs"] = quote_vendor.get("total_jobs", 0)
        quote["vendor_location"] = f"{quote_vendor.get('city', '')}, {quote_vendor.get('country', '')}".strip(", ")
        quote["vendor_certifications"] = quote_vendor.get("certifications", [])
        quote["vendor_industries"] = quote_vendor.get("industries", [])
        quote["vendor_materials"] = quote_vendor.get("materials_handled", [])
        quote["vendor_phone"] = quote_vendor.get("phone")
        quote["vendor_website"] = quote_vendor.get("website")
        quote["vendor_user_id"] = quote_vendor.get("user_id")
        
        # Get vendor user info
        vendor_user = await db.users.find_one({"user_id": quote_vendor.get("user_id")}, {"_id": 0, "email": 1, "name": 1})
        if vendor_user:
            quote["vendor_contact_name"] = vendor_user.get("name")
            quote["vendor_email"] = vendor_user.get("email")
        
        # Get all machines
        machines = await db.machines.find(
            {"vendor_id": quote_vendor["vendor_id"], "is_active": True},
            {"_id": 0}
        ).to_list(20)
        quote["vendor_machines"] = machines
        
        # Get vendor stats
        total_quotes = await db.quotes.count_documents({"vendor_id": quote_vendor["vendor_id"]})
        accepted_quotes = await db.quotes.count_documents({"vendor_id": quote_vendor["vendor_id"], "status": "accepted"})
        quote["vendor_acceptance_rate"] = round((accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0, 1)
    
    # Add RFQ info
    quote["rfq_title"] = rfq.get("title")
    quote["rfq_material"] = rfq.get("material_type")
    quote["rfq_quantity"] = rfq.get("quantity")
    quote["rfq_tolerance"] = rfq.get("tolerance")
    quote["rfq_preferred_payment_terms"] = rfq.get("preferred_payment_terms")
    
    # Get negotiation history
    negotiations = await db.quote_negotiations.find(
        {"quote_id": quote_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    quote["negotiations"] = negotiations
    
    return quote

class NegotiationRequest(BaseModel):
    request_type: str  # "price", "lead_time", "payment_terms", "general"
    message: str
    requested_price: Optional[float] = None
    requested_lead_time: Optional[int] = None
    requested_payment_terms: Optional[str] = None

@api_router.post("/quotes/{quote_id}/negotiate")
async def request_quote_negotiation(quote_id: str, request: NegotiationRequest, user: dict = Depends(get_current_user)):
    """Buyer requests modification/negotiation on a quote"""
    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Only pending quotes can be negotiated
    if quote["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending quotes can be negotiated")
    
    # Verify buyer owns the RFQ
    rfq = await db.rfqs.find_one({"rfq_id": quote["rfq_id"], "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create negotiation record
    negotiation_id = f"neg_{uuid.uuid4().hex[:12]}"
    negotiation_doc = {
        "negotiation_id": negotiation_id,
        "quote_id": quote_id,
        "rfq_id": quote["rfq_id"],
        "buyer_id": user["user_id"],
        "buyer_name": user.get("name", "Buyer"),
        "vendor_id": quote["vendor_id"],
        "request_type": request.request_type,
        "message": request.message,
        "requested_price": request.requested_price,
        "requested_lead_time": request.requested_lead_time,
        "requested_payment_terms": request.requested_payment_terms,
        "original_price": quote["price"],
        "original_lead_time": quote["lead_time_days"],
        "original_payment_terms": quote.get("proposed_payment_terms"),
        "status": "pending",  # pending, accepted, counter_offered, rejected
        "response": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.quote_negotiations.insert_one(negotiation_doc)
    
    # Update quote status to indicate negotiation in progress
    await db.quotes.update_one(
        {"quote_id": quote_id},
        {"$set": {"negotiation_status": "buyer_requested", "updated_at": now}}
    )
    
    # Get vendor info for notification
    vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0})
    
    # Create notification for vendor
    if vendor:
        request_type_labels = {
            "price": "Price Adjustment",
            "lead_time": "Lead Time Change",
            "payment_terms": "Payment Terms",
            "general": "General Request"
        }
        await create_notification(
            user_id=vendor.get("user_id"),
            notification_type="negotiation_request",
            title=f"Negotiation Request: {request_type_labels.get(request.request_type, 'Quote')}",
            message=f"{user.get('name', 'Buyer')} requested changes on quote for '{rfq.get('title', 'RFQ')[:30]}'",
            data={
                "quote_id": quote_id,
                "rfq_id": quote["rfq_id"],
                "negotiation_id": negotiation_id,
                "request_type": request.request_type
            },
            send_email=True,
            email_template="new_message",
            email_data={
                "sender_name": user.get("name", "Buyer"),
                "recipient_name": vendor.get("company_name", "Vendor"),
                "message_preview": f"Negotiation request: {request.message[:150]}",
                "app_url": f"{os.environ.get('APP_URL', 'https://rfq-marketplace-9.preview.emergentagent.com')}/vendor/rfq/{quote['rfq_id']}"
            }
        )
    
    return {
        "message": "Negotiation request sent",
        "negotiation_id": negotiation_id,
        "status": "pending"
    }

class NegotiationResponse(BaseModel):
    action: str  # "accept", "counter", "reject"
    message: Optional[str] = None
    counter_price: Optional[float] = None
    counter_lead_time: Optional[int] = None
    counter_payment_terms: Optional[str] = None

@api_router.post("/quotes/{quote_id}/negotiate/{negotiation_id}/respond")
async def respond_to_negotiation(quote_id: str, negotiation_id: str, response: NegotiationResponse, user: dict = Depends(get_current_user)):
    """Vendor responds to a negotiation request"""
    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor or vendor["vendor_id"] != quote["vendor_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    negotiation = await db.quote_negotiations.find_one(
        {"negotiation_id": negotiation_id, "quote_id": quote_id},
        {"_id": 0}
    )
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    
    if negotiation["status"] != "pending":
        raise HTTPException(status_code=400, detail="Negotiation already resolved")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update negotiation based on action
    if response.action == "accept":
        # Accept the buyer's requested changes
        update_quote = {}
        if negotiation.get("requested_price"):
            update_quote["price"] = negotiation["requested_price"]
        if negotiation.get("requested_lead_time"):
            update_quote["lead_time_days"] = negotiation["requested_lead_time"]
        if negotiation.get("requested_payment_terms"):
            update_quote["proposed_payment_terms"] = negotiation["requested_payment_terms"]
        
        if update_quote:
            update_quote["updated_at"] = now
            update_quote["negotiation_status"] = "resolved"
            await db.quotes.update_one({"quote_id": quote_id}, {"$set": update_quote})
        
        await db.quote_negotiations.update_one(
            {"negotiation_id": negotiation_id},
            {"$set": {
                "status": "accepted",
                "response": response.message,
                "updated_at": now
            }}
        )
        status_msg = "accepted"
        
    elif response.action == "counter":
        # Vendor makes a counter offer
        await db.quote_negotiations.update_one(
            {"negotiation_id": negotiation_id},
            {"$set": {
                "status": "counter_offered",
                "response": response.message,
                "counter_price": response.counter_price,
                "counter_lead_time": response.counter_lead_time,
                "counter_payment_terms": response.counter_payment_terms,
                "updated_at": now
            }}
        )
        await db.quotes.update_one(
            {"quote_id": quote_id},
            {"$set": {"negotiation_status": "vendor_countered", "updated_at": now}}
        )
        status_msg = "counter offered"
        
    else:  # reject
        await db.quote_negotiations.update_one(
            {"negotiation_id": negotiation_id},
            {"$set": {
                "status": "rejected",
                "response": response.message,
                "updated_at": now
            }}
        )
        await db.quotes.update_one(
            {"quote_id": quote_id},
            {"$set": {"negotiation_status": "resolved", "updated_at": now}}
        )
        status_msg = "rejected"
    
    # Notify buyer
    rfq = await db.rfqs.find_one({"rfq_id": quote["rfq_id"]}, {"_id": 0})
    await create_notification(
        user_id=negotiation["buyer_id"],
        notification_type="negotiation_response",
        title=f"Vendor {status_msg} your request",
        message=f"{vendor.get('company_name', 'Vendor')} has {status_msg} your negotiation request for '{rfq.get('title', 'RFQ')[:30]}'",
        data={
            "quote_id": quote_id,
            "rfq_id": quote["rfq_id"],
            "negotiation_id": negotiation_id,
            "action": response.action
        }
    )
    
    # Send WhatsApp notification to buyer about negotiation response
    if whatsapp_service.is_configured():
        buyer = await db.users.find_one({"user_id": negotiation["buyer_id"]}, {"_id": 0, "phone": 1, "user_id": 1})
        if buyer and buyer.get("phone"):
            action_emoji = {"accept": "✅", "counter": "🔄", "reject": "❌"}.get(response.action, "📨")
            
            # Generate magic link for buyer
            magic_result = await generate_magic_link_for_user(buyer["user_id"], f"/buyer/rfq/{quote['rfq_id']}")
            if magic_result.get("success"):
                view_link = f"https://oemlinker.com/magic-login?token={magic_result['token']}"
                link_note = "🔑 _Instant access_"
            else:
                view_link = f"https://oemlinker.com/buyer/rfq/{quote['rfq_id']}"
                link_note = ""
            
            wa_message = f"""{action_emoji} *Negotiation Update!*

📋 *{rfq.get('title', 'Your RFQ')}*

🏭 Vendor: {vendor.get('company_name', 'Vendor')}
📝 Response: {status_msg.title()}"""
            
            if response.action == "counter":
                if response.counter_price:
                    wa_message += f"\n💵 Counter Price: ₹{response.counter_price:,.2f}"
                if response.counter_lead_time:
                    wa_message += f"\n📅 Counter Lead Time: {response.counter_lead_time} days"
            
            wa_message += f"""

🔗 View Details:
{view_link}
{link_note}"""
            asyncio.create_task(whatsapp_service.send_text_message(buyer["phone"], wa_message))
    
    return {
        "message": f"Negotiation {status_msg}",
        "status": response.action
    }

@api_router.post("/quotes/{quote_id}/negotiate/{negotiation_id}/accept-counter")
async def accept_counter_offer(quote_id: str, negotiation_id: str, user: dict = Depends(get_current_user)):
    """Buyer accepts a vendor's counter offer"""
    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    rfq = await db.rfqs.find_one({"rfq_id": quote["rfq_id"], "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    negotiation = await db.quote_negotiations.find_one(
        {"negotiation_id": negotiation_id, "quote_id": quote_id, "status": "counter_offered"},
        {"_id": 0}
    )
    if not negotiation:
        raise HTTPException(status_code=404, detail="Counter offer not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Apply counter offer to quote
    update_quote = {"updated_at": now, "negotiation_status": "resolved"}
    if negotiation.get("counter_price"):
        update_quote["price"] = negotiation["counter_price"]
    if negotiation.get("counter_lead_time"):
        update_quote["lead_time_days"] = negotiation["counter_lead_time"]
    if negotiation.get("counter_payment_terms"):
        update_quote["proposed_payment_terms"] = negotiation["counter_payment_terms"]
    
    await db.quotes.update_one({"quote_id": quote_id}, {"$set": update_quote})
    
    await db.quote_negotiations.update_one(
        {"negotiation_id": negotiation_id},
        {"$set": {"status": "counter_accepted", "updated_at": now}}
    )
    
    # Notify vendor
    vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0})
    if vendor:
        await create_notification(
            user_id=vendor.get("user_id"),
            notification_type="negotiation_response",
            title="Counter Offer Accepted",
            message=f"{user.get('name', 'Buyer')} accepted your counter offer for '{rfq.get('title', 'RFQ')[:30]}'",
            data={
                "quote_id": quote_id,
                "rfq_id": quote["rfq_id"],
                "negotiation_id": negotiation_id
            }
        )
    
    return {"message": "Counter offer accepted", "status": "counter_accepted"}

@api_router.get("/quotes/{quote_id}/negotiations")
async def get_quote_negotiations(quote_id: str, user: dict = Depends(get_current_user)):
    """Get all negotiations for a quote"""
    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check authorization
    rfq = await db.rfqs.find_one({"rfq_id": quote["rfq_id"]}, {"_id": 0})
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    
    is_buyer = rfq and rfq["buyer_id"] == user["user_id"]
    is_vendor = vendor and vendor["vendor_id"] == quote["vendor_id"]
    
    if not is_buyer and not is_vendor and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    negotiations = await db.quote_negotiations.find(
        {"quote_id": quote_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return negotiations

@api_router.post("/quotes/{quote_id}/accept")
async def accept_quote(quote_id: str, user: dict = Depends(get_current_user)):
    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    rfq = await db.rfqs.find_one({"rfq_id": quote["rfq_id"], "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Mark quote as selected
    await db.quotes.update_one(
        {"quote_id": quote_id},
        {"$set": {"is_selected": True, "status": "accepted"}}
    )
    
    # Reject other quotes
    await db.quotes.update_many(
        {"rfq_id": quote["rfq_id"], "quote_id": {"$ne": quote_id}},
        {"$set": {"status": "rejected"}}
    )
    
    # Create order with finalized payment terms from quote
    order_id = f"order_{uuid.uuid4().hex[:12]}"
    po_number = f"PO-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Get payment terms from quote (vendor's proposed terms) 
    payment_terms = quote.get("proposed_payment_terms", "net_30")
    payment_terms_notes = quote.get("payment_terms_notes", "")
    
    order_doc = {
        "order_id": order_id,
        "rfq_id": quote["rfq_id"],
        "quote_id": quote_id,
        "buyer_id": user["user_id"],
        "vendor_id": quote["vendor_id"],
        "total_amount": quote["price"],
        "currency": quote["currency"],
        "status": OrderStatus.PENDING_PAYMENT,
        "payment_status": "pending",
        "payment_terms": payment_terms,
        "payment_terms_label": PAYMENT_TERMS_LABELS.get(payment_terms, payment_terms),
        "payment_terms_notes": payment_terms_notes,
        "po_number": po_number,
        "tracking_updates": [
            {"status": "Order Created", "timestamp": now, "note": f"Quote accepted. PO #{po_number}. Payment Terms: {PAYMENT_TERMS_LABELS.get(payment_terms, payment_terms)}"}
        ],
        "created_at": now,
        "updated_at": now
    }
    
    await db.orders.insert_one(order_doc)
    
    # Update RFQ status
    await db.rfqs.update_one(
        {"rfq_id": quote["rfq_id"]},
        {"$set": {"status": RFQStatus.PO_ISSUED, "updated_at": now}}
    )
    
    # Send email notification to vendor and create in-app notification
    app_url = os.environ.get("APP_URL", "https://rfq-marketplace-9.preview.emergentagent.com")
    vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0})
    if vendor:
        vendor_user = await db.users.find_one({"user_id": vendor.get("user_id")}, {"_id": 0, "email": 1, "name": 1})
        buyer = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "name": 1})
        if vendor_user and vendor_user.get("email"):
            email_data = {
                "vendor_name": vendor_user.get("name", vendor.get("company_name", "Vendor")),
                "rfq_title": rfq.get("title", "RFQ"),
                "buyer_name": buyer.get("name", "Buyer") if buyer else "Buyer",
                "price": f"{quote['price']:.2f}",
                "order_id": order_id,
                "app_url": f"{app_url}/orders/{order_id}"
            }
            subject, html = get_email_template("quote_accepted", email_data)
            asyncio.create_task(send_email_async(vendor_user["email"], subject, html))
        
        # Create in-app notification for vendor
        await create_notification(
            user_id=vendor.get("user_id"),
            notification_type=NotificationType.QUOTE_ACCEPTED,
            title="Quote Accepted!",
            message=f"Your quote for '{rfq.get('title', 'RFQ')}' has been accepted. Order #{po_number}",
            data={"order_id": order_id, "rfq_id": quote["rfq_id"], "quote_id": quote_id, "po_number": po_number}
        )
        
        # Send admin notification for quotation accepted and new PO
        buyer = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "name": 1})
        asyncio.create_task(send_admin_notification("quotation_accepted", {
            "po_number": po_number,
            "order_id": order_id,
            "rfq_title": rfq.get("title", "Untitled"),
            "buyer_name": buyer.get("name", "Unknown") if buyer else "Unknown",
            "vendor_name": vendor.get("company_name", "Unknown"),
            "total_amount": quote["price"],
            "payment_terms": PAYMENT_TERMS_LABELS.get(payment_terms, payment_terms)
        }))
        
        asyncio.create_task(send_admin_notification("new_po", {
            "po_number": po_number,
            "order_id": order_id,
            "rfq_title": rfq.get("title", "Untitled"),
            "buyer_name": buyer.get("name", "Unknown") if buyer else "Unknown",
            "vendor_name": vendor.get("company_name", "Unknown"),
            "total_amount": quote["price"],
            "status": "pending_payment"
        }))
        
        # Send WhatsApp notification to vendor about accepted quote and PO
        if whatsapp_service.is_configured() and vendor.get("phone"):
            # Generate magic link for vendor
            magic_result = await generate_magic_link_for_user(vendor.get("user_id"), f"/vendor/order/{order_id}")
            if magic_result.get("success"):
                order_link = f"https://oemlinker.com/magic-login?token={magic_result['token']}"
                link_note = "🔑 _Instant access_"
            else:
                order_link = f"https://oemlinker.com/vendor/order/{order_id}"
                link_note = ""
            
            wa_message = f"""🎉 *Congratulations! Quote Accepted!*

📋 *{rfq.get('title', 'RFQ')}*

🧾 *PO Number:* {po_number}
💵 Amount: ₹{quote['price']:,.2f}
📅 Lead Time: {quote.get('lead_time_days', 'N/A')} days
💳 Payment Terms: {PAYMENT_TERMS_LABELS.get(payment_terms, payment_terms)}

📦 Next Steps:
1. Wait for payment confirmation
2. Start production after payment
3. Update order status regularly

🔗 View Order:
{order_link}
{link_note}"""
            asyncio.create_task(whatsapp_service.send_text_message(vendor["phone"], wa_message))
    
    return {"message": "Quote accepted", "order_id": order_id}

# ============== ORDER ROUTES ==============

@api_router.get("/orders")
async def list_orders(user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.BUYER:
        orders = await db.orders.find({"buyer_id": user["user_id"]}, {"_id": 0}).to_list(100)
    elif user["role"] == UserRole.VENDOR:
        vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if not vendor:
            return []
        orders = await db.orders.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).to_list(100)
    else:
        orders = await db.orders.find({}, {"_id": 0}).to_list(100)
    
    return orders

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@api_router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    new_status = body.get("status")
    note = body.get("note", "")
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$set": {"status": new_status, "updated_at": now},
            "$push": {"tracking_updates": {"status": new_status, "timestamp": now, "note": note}}
        }
    )
    
    # Determine recipient for notification (buyer or vendor)
    rfq = await db.rfqs.find_one({"rfq_id": order["rfq_id"]}, {"_id": 0, "title": 1})
    rfq_title = rfq.get("title", "Order") if rfq else "Order"
    
    # Status display names
    status_labels = {
        "pending_payment": "Pending Payment",
        "paid": "Payment Confirmed",
        "in_production": "In Production",
        "quality_check": "Quality Check",
        "dispatched": "Dispatched",
        "delivered": "Delivered",
        "completed": "Completed",
        "cancelled": "Cancelled"
    }
    status_label = status_labels.get(new_status, new_status.replace('_', ' ').title())
    
    # Notify both buyer and vendor about status updates
    app_url = os.environ.get("APP_URL", "https://rfq-marketplace-9.preview.emergentagent.com")
    
    # Notify buyer
    await create_notification(
        user_id=order["buyer_id"],
        notification_type=NotificationType.ORDER_STATUS_UPDATE,
        title=f"Order Status: {status_label}",
        message=f"Order for '{rfq_title}' is now {status_label}",
        data={"order_id": order_id, "status": new_status},
        send_email=True,
        email_template="order_status_update",
        email_data={
            "order_id": order.get("po_number", order_id),
            "rfq_title": rfq_title,
            "status": new_status,
            "note": note,
            "recipient_name": "Buyer",
            "app_url": f"{app_url}/orders/{order_id}"
        }
    )
    
    # Notify vendor
    vendor = await db.vendors.find_one({"vendor_id": order["vendor_id"]}, {"_id": 0, "user_id": 1, "phone": 1})
    if vendor:
        await create_notification(
            user_id=vendor["user_id"],
            notification_type=NotificationType.ORDER_STATUS_UPDATE,
            title=f"Order Status: {status_label}",
            message=f"Order for '{rfq_title}' is now {status_label}",
            data={"order_id": order_id, "status": new_status}
        )
    
    # Send WhatsApp notifications for order status updates
    if whatsapp_service.is_configured():
        status_emoji = {
            "pending_payment": "💳",
            "paid": "✅",
            "in_production": "🔨",
            "quality_check": "🔍",
            "dispatched": "🚚",
            "delivered": "📬",
            "completed": "🎉",
            "cancelled": "❌"
        }.get(new_status, "📋")

        # Notify vendor via WhatsApp
        if vendor and vendor.get("phone"):
            # Generate magic link for vendor
            vendor_magic = await generate_magic_link_for_user(vendor.get("user_id"), f"/vendor/order/{order_id}")
            if vendor_magic.get("success"):
                vendor_link = f"https://oemlinker.com/magic-login?token={vendor_magic['token']}"
            else:
                vendor_link = f"https://oemlinker.com/vendor/order/{order_id}"
            
            vendor_wa_message = f"""{status_emoji} *Order Status Update*

🧾 *PO #{order.get('po_number', order_id[:8])}*
📋 {rfq_title}

📊 Status: *{status_label}*"""
            if note:
                vendor_wa_message += f"\n📝 Note: {note}"
            vendor_wa_message += f"""

🔗 View Order:
{vendor_link}
🔑 _Instant access_"""
            asyncio.create_task(whatsapp_service.send_text_message(vendor["phone"], vendor_wa_message))
        
        # Notify buyer via WhatsApp
        buyer = await db.users.find_one({"user_id": order["buyer_id"]}, {"_id": 0, "phone": 1, "user_id": 1})
        if buyer and buyer.get("phone"):
            # Generate magic link for buyer
            buyer_magic = await generate_magic_link_for_user(buyer["user_id"], f"/buyer/order/{order_id}")
            if buyer_magic.get("success"):
                buyer_link = f"https://oemlinker.com/magic-login?token={buyer_magic['token']}"
            else:
                buyer_link = f"https://oemlinker.com/buyer/order/{order_id}"
            
            buyer_wa_message = f"""{status_emoji} *Order Status Update*

🧾 *PO #{order.get('po_number', order_id[:8])}*
📋 {rfq_title}

📊 Status: *{status_label}*"""
            if note:
                buyer_wa_message += f"\n📝 Note: {note}"
            buyer_wa_message += f"""

🔗 View Order:
{buyer_link}
🔑 _Instant access_"""
            asyncio.create_task(whatsapp_service.send_text_message(buyer["phone"], buyer_wa_message))
    
    return {"message": "Status updated", "status": new_status}

# ============== VENDOR RATING SYSTEM ==============

@api_router.post("/orders/{order_id}/rate")
async def rate_vendor(order_id: str, rating: RatingCreate, user: dict = Depends(get_current_user)):
    """Rate a vendor after order completion - buyers only"""
    if user["role"] != UserRole.BUYER:
        raise HTTPException(status_code=403, detail="Only buyers can rate vendors")
    
    order = await db.orders.find_one({"order_id": order_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only allow rating for delivered or completed orders
    if order["status"] not in [OrderStatus.DELIVERED, OrderStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail="Can only rate after order is delivered")
    
    # Check if already rated
    existing_rating = await db.ratings.find_one({"order_id": order_id})
    if existing_rating:
        raise HTTPException(status_code=400, detail="Order already rated")
    
    # Validate ratings
    for r in [rating.overall_rating, rating.quality_rating, rating.communication_rating, rating.delivery_rating]:
        if r < 1 or r > 5:
            raise HTTPException(status_code=400, detail="Ratings must be between 1 and 5")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get RFQ info for context
    rfq = await db.rfqs.find_one({"rfq_id": order["rfq_id"]}, {"_id": 0, "title": 1})
    
    rating_doc = {
        "rating_id": f"rating_{uuid.uuid4().hex[:12]}",
        "order_id": order_id,
        "rfq_id": order["rfq_id"],
        "rfq_title": rfq.get("title", "") if rfq else "",
        "vendor_id": order["vendor_id"],
        "buyer_id": user["user_id"],
        "buyer_name": user.get("name", user.get("company_name", "Anonymous")),
        "overall_rating": rating.overall_rating,
        "quality_rating": rating.quality_rating,
        "communication_rating": rating.communication_rating,
        "delivery_rating": rating.delivery_rating,
        "review_text": rating.review_text,
        "would_recommend": rating.would_recommend,
        "created_at": now
    }
    
    await db.ratings.insert_one(rating_doc)
    
    # Update vendor's average rating
    all_ratings = await db.ratings.find({"vendor_id": order["vendor_id"]}, {"_id": 0}).to_list(1000)
    avg_rating = sum(r["overall_rating"] for r in all_ratings) / len(all_ratings)
    
    await db.vendors.update_one(
        {"vendor_id": order["vendor_id"]},
        {"$set": {"rating": round(avg_rating, 2), "total_reviews": len(all_ratings)}}
    )
    
    # Mark order as completed and rated
    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$set": {"status": OrderStatus.COMPLETED, "is_rated": True, "updated_at": now},
            "$push": {"tracking_updates": {"status": "completed", "timestamp": now, "note": "Order rated by buyer"}}
        }
    )
    
    return {"message": "Rating submitted", "rating_id": rating_doc["rating_id"]}

@api_router.get("/vendors/{vendor_id}/ratings")
async def get_vendor_ratings(vendor_id: str, limit: int = 20):
    """Get ratings for a vendor - public endpoint"""
    ratings = await db.ratings.find(
        {"vendor_id": vendor_id}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    # Calculate stats
    if ratings:
        stats = {
            "total_reviews": len(ratings),
            "average_overall": round(sum(r["overall_rating"] for r in ratings) / len(ratings), 2),
            "average_quality": round(sum(r["quality_rating"] for r in ratings) / len(ratings), 2),
            "average_communication": round(sum(r["communication_rating"] for r in ratings) / len(ratings), 2),
            "average_delivery": round(sum(r["delivery_rating"] for r in ratings) / len(ratings), 2),
            "recommendation_rate": round(sum(1 for r in ratings if r["would_recommend"]) / len(ratings) * 100, 1)
        }
    else:
        stats = {
            "total_reviews": 0,
            "average_overall": 0,
            "average_quality": 0,
            "average_communication": 0,
            "average_delivery": 0,
            "recommendation_rate": 0
        }
    
    return {"ratings": ratings, "stats": stats}

@api_router.get("/orders/{order_id}/rating")
async def get_order_rating(order_id: str, user: dict = Depends(get_current_user)):
    """Check if an order has been rated"""
    rating = await db.ratings.find_one({"order_id": order_id}, {"_id": 0})
    return {"rated": rating is not None, "rating": rating}

# ============== ENHANCED ORDER MANAGEMENT ==============

@api_router.get("/orders/{order_id}/details")
async def get_order_details(order_id: str, user: dict = Depends(get_current_user)):
    """Get full order details with related info"""
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get vendor info
    vendor = await db.vendors.find_one({"vendor_id": order["vendor_id"]}, {"_id": 0})
    
    # Get quote info
    quote = await db.quotes.find_one({"quote_id": order["quote_id"]}, {"_id": 0})
    
    # Get RFQ info
    rfq = await db.rfqs.find_one({"rfq_id": order["rfq_id"]}, {"_id": 0})
    
    # Get buyer info
    buyer = await db.users.find_one({"user_id": order["buyer_id"]}, {"_id": 0, "password_hash": 0})
    
    # Get rating if exists
    rating = await db.ratings.find_one({"order_id": order_id}, {"_id": 0})
    
    return {
        "order": order,
        "vendor": {
            "vendor_id": vendor.get("vendor_id") if vendor else None,
            "company_name": vendor.get("company_name") if vendor else "Unknown",
            "rating": vendor.get("rating", 0) if vendor else 0,
            "email": vendor.get("contact_email") if vendor else None,
            "phone": vendor.get("contact_phone") if vendor else None,
            "address": f"{vendor.get('city', '')}, {vendor.get('country', '')}".strip(", ") if vendor else ""
        },
        "buyer": {
            "user_id": buyer.get("user_id") if buyer else None,
            "name": buyer.get("name", buyer.get("company_name", "Unknown")) if buyer else "Unknown",
            "email": buyer.get("email") if buyer else None
        },
        "quote": {
            "price": quote.get("price") if quote else 0,
            "lead_time_days": quote.get("lead_time_days") if quote else 0,
            "notes": quote.get("notes") if quote else ""
        },
        "rfq": {
            "rfq_id": rfq.get("rfq_id") if rfq else None,
            "title": rfq.get("title") if rfq else "Unknown",
            "material_type": rfq.get("material_type") if rfq else "",
            "quantity": rfq.get("quantity", 1) if rfq else 1
        },
        "rating": rating,
        "is_rated": rating is not None
    }

@api_router.post("/orders/{order_id}/confirm-delivery")
async def confirm_delivery(order_id: str, user: dict = Depends(get_current_user)):
    """Buyer confirms delivery - triggers ability to rate"""
    if user["role"] != UserRole.BUYER:
        raise HTTPException(status_code=403, detail="Only buyers can confirm delivery")
    
    order = await db.orders.find_one({"order_id": order_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] not in [OrderStatus.DISPATCHED, OrderStatus.DELIVERED]:
        raise HTTPException(status_code=400, detail="Order must be dispatched or delivered to confirm")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$set": {"status": OrderStatus.DELIVERED, "delivery_confirmed": True, "delivered_at": now, "updated_at": now},
            "$push": {"tracking_updates": {"status": "delivered", "timestamp": now, "note": "Delivery confirmed by buyer"}}
        }
    )
    
    # Send email to vendor
    try:
        vendor = await db.vendors.find_one({"vendor_id": order["vendor_id"]}, {"_id": 0})
        if vendor and vendor.get("contact_email"):
            email_data = {
                "order_id": order_id,
                "status": "Delivered - Confirmed by buyer",
                "app_url": f"{os.environ.get('CORS_ORIGINS', '').split(',')[0]}/orders/{order_id}"
            }
            subject, html = get_email_template("order_status_update", email_data)
            asyncio.create_task(send_email_async(vendor["contact_email"], subject, html))
    except Exception as e:
        print(f"Email error: {e}")
    
    return {"message": "Delivery confirmed", "status": OrderStatus.DELIVERED}

@api_router.post("/orders/{order_id}/add-tracking")
async def add_tracking_info(order_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Vendor adds tracking info like courier and tracking number"""
    if user["role"] != UserRole.VENDOR:
        raise HTTPException(status_code=403, detail="Only vendors can add tracking info")
    
    body = await request.json()
    courier = body.get("courier", "")
    tracking_number = body.get("tracking_number", "")
    estimated_delivery = body.get("estimated_delivery", "")
    note = body.get("note", "")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    order = await db.orders.find_one({"order_id": order_id, "vendor_id": vendor["vendor_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    tracking_info = {
        "courier": courier,
        "tracking_number": tracking_number,
        "estimated_delivery": estimated_delivery,
        "added_at": now
    }
    
    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$set": {
                "tracking_info": tracking_info,
                "status": OrderStatus.DISPATCHED,
                "updated_at": now
            },
            "$push": {"tracking_updates": {
                "status": "dispatched", 
                "timestamp": now, 
                "note": f"Shipped via {courier}. Tracking: {tracking_number}. {note}".strip()
            }}
        }
    )
    
    # Send email to buyer
    try:
        buyer = await db.users.find_one({"user_id": order["buyer_id"]}, {"_id": 0})
        if buyer and buyer.get("email"):
            email_data = {
                "order_id": order_id,
                "status": f"Dispatched - Track via {courier}: {tracking_number}",
                "app_url": f"{os.environ.get('CORS_ORIGINS', '').split(',')[0]}/orders/{order_id}"
            }
            subject, html = get_email_template("order_status_update", email_data)
            asyncio.create_task(send_email_async(buyer["email"], subject, html))
    except Exception as e:
        print(f"Email error: {e}")
    
    return {"message": "Tracking info added", "tracking_info": tracking_info}

# ============== PAYMENT ROUTES ==============

@api_router.post("/payments/checkout")
async def create_checkout_session(request: Request, user: dict = Depends(get_current_user)):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    
    body = await request.json()
    order_id = body.get("order_id")
    origin_url = body.get("origin_url")
    
    if not order_id or not origin_url:
        raise HTTPException(status_code=400, detail="order_id and origin_url required")
    
    order = await db.orders.find_one({"order_id": order_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    webhook_url = f"{request.base_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    success_url = f"{origin_url}/orders/{order_id}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/orders/{order_id}"
    
    checkout_request = CheckoutSessionRequest(
        amount=float(order["total_amount"]),
        currency=order["currency"].lower(),
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "order_id": order_id,
            "buyer_id": user["user_id"]
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    await db.payment_transactions.insert_one({
        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
        "order_id": order_id,
        "user_id": user["user_id"],
        "session_id": session.session_id,
        "amount": float(order["total_amount"]),
        "currency": order["currency"],
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, user: dict = Depends(get_current_user)):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")
    
    status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction if paid
    if status.payment_status == "paid":
        txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if txn and txn.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid"}}
            )
            
            # Update order status
            await db.orders.update_one(
                {"order_id": txn["order_id"]},
                {
                    "$set": {
                        "payment_status": "paid",
                        "status": OrderStatus.PAID,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    },
                    "$push": {"tracking_updates": {
                        "status": "Payment Received",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "note": "Payment confirmed"
                    }}
                }
            )
    
    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")
    
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            metadata = webhook_response.metadata
            
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid"}}
            )
            
            if "order_id" in metadata:
                await db.orders.update_one(
                    {"order_id": metadata["order_id"]},
                    {
                        "$set": {
                            "payment_status": "paid",
                            "status": OrderStatus.PAID,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

# ============== ADMIN ROUTES ==============

@api_router.get("/admin/vendors/pending")
async def get_pending_vendors(user: dict = Depends(get_current_user)):
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    vendors = await db.vendors.find({"is_approved": False}, {"_id": 0}).to_list(100)
    return vendors

@api_router.post("/admin/vendors/{vendor_id}/approve")
async def approve_vendor(vendor_id: str, user: dict = Depends(get_current_user)):
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.vendors.update_one(
        {"vendor_id": vendor_id},
        {"$set": {"is_approved": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return {"message": "Vendor approved"}

@api_router.get("/admin/stats")
async def get_admin_stats(user: dict = Depends(get_current_user)):
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_users = await db.users.count_documents({})
    total_vendors = await db.vendors.count_documents({})
    approved_vendors = await db.vendors.count_documents({"is_approved": True})
    total_rfqs = await db.rfqs.count_documents({})
    total_orders = await db.orders.count_documents({})
    
    return {
        "total_users": total_users,
        "total_vendors": total_vendors,
        "approved_vendors": approved_vendors,
        "pending_vendors": total_vendors - approved_vendors,
        "total_rfqs": total_rfqs,
        "total_orders": total_orders,
        "total_quotes": await db.quotes.count_documents({}),
        "total_ndas": await db.ndas.count_documents({})
    }

# ============== ADMIN - USER MANAGEMENT ==============

@api_router.get("/admin/users")
async def admin_list_users(user: dict = Depends(get_current_user), role: Optional[str] = None, search: Optional[str] = None):
    """List all users with optional filtering"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if role:
        query["role"] = role
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(200)
    return users

class AdminUserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "buyer"
    custom_role: Optional[str] = None
    company_name: Optional[str] = None

@api_router.post("/admin/users")
async def admin_create_user(user_data: AdminUserCreate, user: dict = Depends(get_current_user)):
    """Admin creates a new user"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    new_user = {
        "user_id": user_id,
        "email": user_data.email.lower(),
        "password_hash": pwd_context.hash(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "custom_role": user_data.custom_role,
        "company_name": user_data.company_name,
        "created_at": now
    }
    
    await db.users.insert_one(new_user)
    
    # If vendor role, create vendor profile
    if user_data.role == "vendor":
        vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
        vendor_profile = {
            "vendor_id": vendor_id,
            "user_id": user_id,
            "company_name": user_data.company_name or user_data.name,
            "is_approved": True,
            "rating": 0,
            "total_jobs": 0,
            "created_at": now
        }
        await db.vendors.insert_one(vendor_profile)
    
    return {"message": "User created successfully", "user_id": user_id}

class AdminVendorCreate(BaseModel):
    email: str
    password: str
    name: str
    company_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    certifications: Optional[List[str]] = []
    industries: Optional[List[str]] = []
    materials_handled: Optional[List[str]] = []

@api_router.post("/admin/vendors")
async def admin_create_vendor(vendor_data: AdminVendorCreate, user: dict = Depends(get_current_user)):
    """Admin creates a new vendor with user account"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": vendor_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    new_user = {
        "user_id": user_id,
        "email": vendor_data.email.lower(),
        "password_hash": pwd_context.hash(vendor_data.password),
        "name": vendor_data.name,
        "role": "vendor",
        "company_name": vendor_data.company_name,
        "created_at": now
    }
    
    await db.users.insert_one(new_user)
    
    # Create vendor profile
    vendor_profile = {
        "vendor_id": vendor_id,
        "user_id": user_id,
        "company_name": vendor_data.company_name,
        "description": vendor_data.description,
        "address": vendor_data.address,
        "city": vendor_data.city,
        "country": vendor_data.country,
        "phone": vendor_data.phone,
        "website": vendor_data.website,
        "certifications": vendor_data.certifications or [],
        "industries": vendor_data.industries or [],
        "materials_handled": vendor_data.materials_handled or [],
        "is_approved": True,
        "rating": 0,
        "total_jobs": 0,
        "created_at": now
    }
    
    await db.vendors.insert_one(vendor_profile)
    
    return {"message": "Vendor created successfully", "user_id": user_id, "vendor_id": vendor_id}

@api_router.get("/admin/users/{user_id}")
async def admin_get_user(user_id: str, user: dict = Depends(get_current_user)):
    """Get user details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    target_user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get related vendor profile if exists
    vendor = await db.vendors.find_one({"user_id": user_id}, {"_id": 0})
    
    return {**target_user, "vendor_profile": vendor}

@api_router.put("/admin/users/{user_id}")
async def admin_update_user(user_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update user details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    allowed_fields = ["name", "role", "custom_role", "company_name"]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    result = await db.users.update_one({"user_id": user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User updated successfully"}

@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user: dict = Depends(get_current_user)):
    """Delete a user and associated data"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Prevent self-deletion
    if user_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    target_user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get vendor phone number before deletion for WhatsApp session cleanup
    vendor = await db.vendors.find_one({"user_id": user_id}, {"_id": 0, "phone": 1})
    vendor_phone = vendor.get("phone") if vendor else None
    
    # Also check if user has phone directly
    user_phone = target_user.get("phone")
    
    # Delete associated data
    await db.vendors.delete_many({"user_id": user_id})
    await db.machines.delete_many({"vendor_id": {"$regex": user_id}})
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.notifications.delete_many({"user_id": user_id})
    await db.users.delete_one({"user_id": user_id})
    
    # Clean up WhatsApp session
    if vendor_phone:
        cleanup_whatsapp_session(vendor_phone)
    elif user_phone:
        cleanup_whatsapp_session(user_phone)
    
    logger.info(f"User deleted by admin: {target_user.get('email')} (ID: {user_id})")
    return {"message": "User deleted successfully"}

# ============== ADMIN - RFQ MANAGEMENT ==============

@api_router.get("/admin/rfqs")
async def admin_list_rfqs(user: dict = Depends(get_current_user), status: Optional[str] = None, search: Optional[str] = None):
    """List all RFQs with optional filtering"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"rfq_id": {"$regex": search, "$options": "i"}}
        ]
    
    rfqs = await db.rfqs.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Enrich with buyer info
    for rfq in rfqs:
        buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "name": 1, "email": 1})
        rfq["buyer_info"] = buyer
    
    return rfqs

@api_router.get("/admin/rfqs/{rfq_id}")
async def admin_get_rfq(rfq_id: str, user: dict = Depends(get_current_user)):
    """Get RFQ details with all related data"""
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "rfqs.view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get buyer info with more details
    buyer = await db.users.find_one(
        {"user_id": rfq["buyer_id"]}, 
        {"_id": 0, "name": 1, "email": 1, "phone": 1, "company_name": 1, "city": 1, "state": 1, "country": 1}
    )
    
    # Get drawings with fresh presigned URLs
    drawings = await db.drawings.find({"rfq_id": rfq_id}, {"_id": 0, "file_data": 0}).to_list(20)
    
    # Generate fresh presigned URLs for drawings
    from app.services.s3_storage_service import get_presigned_url
    for drawing in drawings:
        try:
            # Get the S3 path from the drawing
            s3_path = drawing.get("s3_path")
            
            if s3_path:
                # Generate fresh presigned URL (valid for 1 hour)
                presigned_url = get_presigned_url(s3_path, expiration=3600)
                drawing["file_url"] = presigned_url
                drawing["view_url"] = presigned_url
                drawing["download_url"] = presigned_url
            elif drawing.get("s3_url"):
                # Extract S3 key from full URL and generate presigned URL
                s3_url = drawing.get("s3_url")
                # Parse URL to get key: https://bucket.s3.region.amazonaws.com/path/to/file
                if ".amazonaws.com/" in s3_url:
                    s3_key = s3_url.split(".amazonaws.com/")[1]
                    presigned_url = get_presigned_url(s3_key, expiration=3600)
                    drawing["file_url"] = presigned_url
                    drawing["view_url"] = presigned_url
                    drawing["download_url"] = presigned_url
                else:
                    drawing["file_url"] = s3_url
                    drawing["view_url"] = s3_url
                    drawing["download_url"] = s3_url
            
            # Determine if file is previewable (image or PDF)
            file_type = drawing.get("file_type", "").lower()
            drawing["is_previewable"] = file_type in ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"]
            drawing["is_image"] = file_type.startswith("image/")
            drawing["is_pdf"] = file_type == "application/pdf"
            
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL for drawing {drawing.get('drawing_id')}: {e}")
            # Fallback to stored URL
            drawing["file_url"] = drawing.get("s3_url", "")
    
    # Get quotes
    quotes = await db.quotes.find({"rfq_id": rfq_id}, {"_id": 0}).to_list(50)
    
    # Enrich quotes with vendor info
    for quote in quotes:
        vendor = await db.vendors.find_one(
            {"vendor_id": quote["vendor_id"]}, 
            {"_id": 0, "company_name": 1, "city": 1, "state": 1}
        )
        quote["vendor_info"] = vendor
    
    # Get matched vendors info
    matched_vendors = []
    for mv in rfq.get("matched_vendors", []):
        vendor = await db.vendors.find_one(
            {"vendor_id": mv.get("vendor_id")}, 
            {"_id": 0, "company_name": 1, "city": 1, "state": 1, "phone": 1}
        )
        if vendor:
            matched_vendors.append({
                **mv,
                "vendor_details": vendor
            })
    
    # Get AI analysis summary
    ai_analysis = rfq.get("ai_analysis", {})
    
    return {
        **rfq,
        "buyer_info": buyer,
        "drawings": drawings,
        "quotes": quotes,
        "matched_vendors_details": matched_vendors,
        "ai_summary": {
            "recommended_processes": ai_analysis.get("recommended_processes", []),
            "overall_dimensions": ai_analysis.get("overall_dimensions", {}),
            "material_suggestions": ai_analysis.get("material_suggestions", []),
            "complexity_score": ai_analysis.get("complexity_score", 0),
            "part_geometry": ai_analysis.get("part_geometry", "")
        }
    }


@api_router.get("/admin/rfqs/{rfq_id}/pdf")
async def admin_generate_rfq_pdf(rfq_id: str, user: dict = Depends(get_current_user)):
    """Generate and return RFQ as a professionally formatted PDF document"""
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "rfqs.view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get buyer info
    buyer = await db.users.find_one(
        {"user_id": rfq["buyer_id"]}, 
        {"_id": 0, "name": 1, "email": 1, "phone": 1, "company_name": 1, "city": 1, "state": 1}
    )
    
    # Get drawings with presigned URLs
    drawings = await db.drawings.find({"rfq_id": rfq_id}, {"_id": 0, "file_data": 0}).to_list(20)
    from app.services.s3_storage_service import get_presigned_url
    for drawing in drawings:
        s3_path = drawing.get("s3_path")
        if s3_path:
            try:
                drawing["file_url"] = get_presigned_url(s3_path, expiration=86400)  # 24 hours for PDF links
            except:
                drawing["file_url"] = drawing.get("s3_url", "")
    
    # Get AI analysis
    ai_analysis = rfq.get("ai_analysis", {})
    
    # Generate PDF using reportlab with improved layout
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from io import BytesIO
    
    # Page dimensions
    PAGE_WIDTH = A4[0]
    PAGE_HEIGHT = A4[1]
    MARGIN = 15 * mm
    CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)
    
    buffer = BytesIO()
    
    # Custom page template with header and footer
    def add_page_number(canvas, doc):
        canvas.saveState()
        # Footer line
        canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 15*mm, PAGE_WIDTH - MARGIN, 15*mm)
        # Footer text
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#94a3b8'))
        canvas.drawString(MARGIN, 10*mm, f"Generated by OEMLinker • {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}")
        canvas.drawRightString(PAGE_WIDTH - MARGIN, 10*mm, f"Page {doc.page}")
        canvas.restoreState()
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=MARGIN, 
        leftMargin=MARGIN, 
        topMargin=MARGIN, 
        bottomMargin=25*mm
    )
    
    # Define colors
    ORANGE = colors.HexColor('#f97316')
    ORANGE_LIGHT = colors.HexColor('#fff7ed')
    ORANGE_BORDER = colors.HexColor('#fed7aa')
    SLATE_900 = colors.HexColor('#0f172a')
    SLATE_700 = colors.HexColor('#334155')
    SLATE_500 = colors.HexColor('#64748b')
    SLATE_200 = colors.HexColor('#e2e8f0')
    SLATE_100 = colors.HexColor('#f1f5f9')
    BLUE_50 = colors.HexColor('#eff6ff')
    BLUE_600 = colors.HexColor('#2563eb')
    GREEN_50 = colors.HexColor('#f0fdf4')
    GREEN_700 = colors.HexColor('#15803d')
    
    # Styles
    styles = getSampleStyleSheet()
    
    logo_style = ParagraphStyle(
        'Logo', fontSize=22, textColor=ORANGE, fontName='Helvetica-Bold', spaceAfter=0
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', fontSize=10, textColor=SLATE_500, spaceAfter=0
    )
    section_header_style = ParagraphStyle(
        'SectionHeader', fontSize=11, textColor=SLATE_900, fontName='Helvetica-Bold',
        spaceBefore=12, spaceAfter=6, leftIndent=0
    )
    label_style = ParagraphStyle(
        'Label', fontSize=9, textColor=SLATE_500, spaceAfter=2
    )
    value_style = ParagraphStyle(
        'Value', fontSize=10, textColor=SLATE_700, spaceAfter=4, leading=14
    )
    value_bold_style = ParagraphStyle(
        'ValueBold', fontSize=10, textColor=SLATE_900, fontName='Helvetica-Bold', spaceAfter=4
    )
    description_style = ParagraphStyle(
        'Description', fontSize=9, textColor=SLATE_700, leading=13, 
        spaceAfter=4, wordWrap='LTR', splitLongWords=True
    )
    link_style = ParagraphStyle(
        'Link', fontSize=9, textColor=ORANGE
    )
    
    elements = []
    
    # ===== HEADER =====
    header_left = Paragraph('<b>OEMLinker</b>', logo_style)
    header_right_text = f'''<para align="right">
        <b>REQUEST FOR QUOTATION</b><br/>
        <font size="9" color="#64748b">{rfq_id}</font>
    </para>'''
    header_right = Paragraph(header_right_text, ParagraphStyle('HeaderRight', fontSize=14, textColor=SLATE_900, alignment=TA_RIGHT))
    
    header_table = Table([[header_left, header_right]], colWidths=[90*mm, 90*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3*mm))
    
    # Header divider
    elements.append(HRFlowable(width="100%", thickness=1, color=ORANGE, spaceBefore=2, spaceAfter=8))
    
    # ===== RFQ INFO BAR =====
    rfq_date = rfq.get("created_at", "")
    if rfq_date:
        try:
            rfq_date = datetime.fromisoformat(rfq_date.replace('Z', '+00:00')).strftime("%d %b %Y")
        except:
            rfq_date = "N/A"
    
    status = rfq.get("status", "N/A").upper()
    status_color = GREEN_700 if status in ["COMPLETED", "QUOTED"] else ORANGE if status == "MATCHING" else SLATE_700
    
    info_data = [[
        Paragraph(f'<b>Date:</b> {rfq_date}', value_style),
        Paragraph(f'<b>Status:</b> <font color="{status_color.hexval()}">{status}</font>', value_style),
        Paragraph(f'<b>Material:</b> {rfq.get("material_type", "N/A")}', value_style)
    ]]
    info_table = Table(info_data, colWidths=[60*mm, 60*mm, 60*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ORANGE_LIGHT),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, ORANGE_BORDER),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8*mm))
    
    # ===== BUYER DETAILS SECTION =====
    elements.append(Paragraph('BUYER DETAILS', section_header_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200, spaceBefore=0, spaceAfter=6))
    
    buyer_name = buyer.get("name", "N/A") if buyer else "N/A"
    buyer_company = buyer.get("company_name", "N/A") if buyer else "N/A"
    buyer_email = buyer.get("email", "N/A") if buyer else "N/A"
    buyer_phone = buyer.get("phone", "N/A") if buyer else "N/A"
    buyer_city = buyer.get("city", "") if buyer else ""
    buyer_state = buyer.get("state", "") if buyer else ""
    buyer_location = f"{buyer_city}, {buyer_state}".strip(", ") or "N/A"
    
    buyer_data = [
        [Paragraph('Name', label_style), Paragraph(buyer_name, value_bold_style),
         Paragraph('Company', label_style), Paragraph(buyer_company, value_bold_style)],
        [Paragraph('Email', label_style), Paragraph(buyer_email, value_style),
         Paragraph('Phone', label_style), Paragraph(buyer_phone, value_style)],
        [Paragraph('Location', label_style), Paragraph(buyer_location, value_style), '', '']
    ]
    buyer_table = Table(buyer_data, colWidths=[25*mm, 60*mm, 25*mm, 60*mm])
    buyer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(buyer_table)
    elements.append(Spacer(1, 6*mm))
    
    # ===== RFQ DETAILS SECTION =====
    elements.append(Paragraph('RFQ DETAILS', section_header_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200, spaceBefore=0, spaceAfter=6))
    
    # Part name prominently
    elements.append(Paragraph('Part Name / Title', label_style))
    elements.append(Paragraph(f'<b>{rfq.get("title", "N/A")}</b>', 
        ParagraphStyle('PartName', fontSize=14, textColor=SLATE_900, fontName='Helvetica-Bold', spaceAfter=8)))
    
    # Details grid
    rfq_grid_data = [
        [Paragraph('Quantity', label_style), Paragraph(str(rfq.get("quantity", "N/A")), value_bold_style),
         Paragraph('Tolerance', label_style), Paragraph(f'{rfq.get("tolerance", "N/A")} mm' if rfq.get("tolerance") else 'N/A', value_style)],
        [Paragraph('Surface Finish', label_style), Paragraph(rfq.get("surface_finish", "N/A") or 'N/A', value_style),
         Paragraph('Deadline', label_style), Paragraph(rfq.get("deadline", "As per discussion") or 'As per discussion', value_style)]
    ]
    rfq_grid = Table(rfq_grid_data, colWidths=[30*mm, 55*mm, 30*mm, 55*mm])
    rfq_grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(rfq_grid)
    
    # Delivery location
    delivery_loc = rfq.get("delivery_location") or rfq.get("delivery_address", "")
    if delivery_loc:
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph('Delivery Location', label_style))
        elements.append(Paragraph(delivery_loc, value_style))
    
    elements.append(Spacer(1, 6*mm))
    
    # ===== DESCRIPTION / SPECIFICATIONS =====
    description = rfq.get("description", "").strip()
    if description:
        elements.append(Paragraph('DESCRIPTION / SPECIFICATIONS', section_header_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200, spaceBefore=0, spaceAfter=6))
        
        # Wrap long text properly
        desc_text = description.replace('\n', '<br/>')
        desc_para = Paragraph(desc_text, description_style)
        
        # Put in a bordered box
        desc_table = Table([[desc_para]], colWidths=[CONTENT_WIDTH - 4*mm])
        desc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), SLATE_100),
            ('BOX', (0, 0), (-1, -1), 0.5, SLATE_200),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(desc_table)
        elements.append(Spacer(1, 6*mm))
    
    # ===== TECHNICAL ANALYSIS (AI) =====
    if ai_analysis and (ai_analysis.get("recommended_processes") or ai_analysis.get("overall_dimensions") or ai_analysis.get("part_geometry")):
        elements.append(Paragraph('TECHNICAL ANALYSIS', section_header_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200, spaceBefore=0, spaceAfter=6))
        
        tech_content = []
        
        # Recommended Processes
        processes = ai_analysis.get("recommended_processes", [])
        if processes:
            proc_text = ', '.join(processes[:6])
            tech_content.append([Paragraph('Recommended Processes', label_style), Paragraph(proc_text, value_style)])
        
        # Dimensions
        dims = ai_analysis.get("overall_dimensions", {})
        if dims:
            dim_parts = []
            if dims.get("length"): dim_parts.append(f"L: {dims['length']}mm")
            if dims.get("width"): dim_parts.append(f"W: {dims['width']}mm")
            if dims.get("height"): dim_parts.append(f"H: {dims['height']}mm")
            if dims.get("diameter"): dim_parts.append(f"Ø: {dims['diameter']}mm")
            if dim_parts:
                tech_content.append([Paragraph('Dimensions', label_style), Paragraph(' × '.join(dim_parts), value_style)])
        
        # Part Geometry
        geometry = ai_analysis.get("part_geometry", "")
        if geometry:
            tech_content.append([Paragraph('Part Geometry', label_style), Paragraph(geometry, value_style)])
        
        # Complexity
        complexity = ai_analysis.get("complexity_score", 0)
        if complexity:
            tech_content.append([Paragraph('Complexity', label_style), Paragraph(f'{complexity}/10', value_style)])
        
        if tech_content:
            tech_table = Table(tech_content, colWidths=[45*mm, CONTENT_WIDTH - 49*mm])
            tech_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), BLUE_50),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#bfdbfe')),
            ]))
            elements.append(tech_table)
        elements.append(Spacer(1, 6*mm))
    
    # ===== ATTACHMENTS / DRAWINGS =====
    if drawings:
        elements.append(Paragraph(f'ATTACHMENTS ({len(drawings)})', section_header_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200, spaceBefore=0, spaceAfter=6))
        
        for i, drawing in enumerate(drawings, 1):
            filename = drawing.get("filename", drawing.get("original_filename", f"Drawing {i}"))
            file_type = drawing.get("file_type", "File")
            file_size = drawing.get("file_size", 0)
            file_size_str = f"{file_size / 1024:.1f} KB" if file_size > 0 else ""
            file_url = drawing.get("file_url", "")
            
            # Create attachment row
            attach_text = f'<b>{i}. {filename}</b>'
            if file_size_str:
                attach_text += f' <font size="8" color="#64748b">({file_size_str})</font>'
            
            elements.append(Paragraph(attach_text, value_style))
            
            if file_url:
                # Truncate long URLs for display
                display_url = file_url[:80] + "..." if len(file_url) > 80 else file_url
                elements.append(Paragraph(
                    f'<link href="{file_url}"><font color="#f97316" size="8">View/Download: {display_url}</font></link>',
                    ParagraphStyle('AttachLink', fontSize=8, textColor=SLATE_500, leftIndent=10)
                ))
            elements.append(Spacer(1, 2*mm))
        
        elements.append(Spacer(1, 4*mm))
    
    # ===== NOTES =====
    notes = rfq.get("notes", "").strip()
    if notes:
        elements.append(Paragraph('ADDITIONAL NOTES', section_header_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200, spaceBefore=0, spaceAfter=6))
        notes_text = notes.replace('\n', '<br/>')
        elements.append(Paragraph(notes_text, description_style))
        elements.append(Spacer(1, 6*mm))
    
    # ===== FOOTER SPACER =====
    elements.append(Spacer(1, 10*mm))
    
    # Build PDF with page numbers
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    
    # Return as downloadable file
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=RFQ_{rfq_id}.pdf"
        }
    )

@api_router.put("/admin/rfqs/{rfq_id}")
async def admin_update_rfq(rfq_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update RFQ details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    allowed_fields = ["title", "description", "material_type", "quantity", "tolerance", "surface_finish", "status", "deadline"]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.rfqs.update_one({"rfq_id": rfq_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    return {"message": "RFQ updated successfully"}

@api_router.delete("/admin/rfqs/{rfq_id}")
async def admin_delete_rfq(rfq_id: str, user: dict = Depends(get_current_user)):
    """Delete an RFQ and associated data"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Delete associated data
    await db.drawings.delete_many({"rfq_id": rfq_id})
    await db.quotes.delete_many({"rfq_id": rfq_id})
    await db.rfqs.delete_one({"rfq_id": rfq_id})
    
    return {"message": "RFQ deleted successfully"}


# ============== ADMIN - MANUAL RFQ-VENDOR MATCHING ==============

@api_router.post("/admin/rfq/{rfq_id}/match-vendors")
async def admin_manual_match_vendors(
    rfq_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Manually match one or more vendors to an RFQ.
    Creates match records and sends notifications to both vendors and buyer.
    """
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "rfqs.match_vendors")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'rfqs.match_vendors' permission.")
    
    body = await request.json()
    vendor_ids = body.get("vendor_ids", [])
    
    if not vendor_ids:
        raise HTTPException(status_code=400, detail="vendor_ids array is required")
    
    # Validate RFQ exists
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get buyer info
    buyer = await db.users.find_one({"user_id": rfq.get("buyer_id")}, {"_id": 0})
    
    # Validate all vendor IDs exist
    valid_vendors = []
    for vid in vendor_ids:
        vendor = await db.vendors.find_one({"vendor_id": vid}, {"_id": 0})
        if vendor:
            valid_vendors.append(vendor)
        else:
            logger.warning(f"Vendor {vid} not found during manual match")
    
    if not valid_vendors:
        raise HTTPException(status_code=400, detail="No valid vendors found")
    
    # Create match records
    matches_created = []
    now = datetime.now(timezone.utc).isoformat()
    
    for vendor in valid_vendors:
        match_record = {
            "match_id": f"match_{uuid.uuid4().hex[:12]}",
            "rfq_id": rfq_id,
            "vendor_id": vendor["vendor_id"],
            "matched_by": user["user_id"],
            "matched_by_name": user.get("name", user.get("email", "Unknown")),
            "status": "matched",  # matched, viewed, responded, quoted
            "match_type": "manual",  # manual vs auto
            "created_at": now,
            "updated_at": now
        }
        
        # Check if already matched
        existing = await db.rfq_vendor_matches.find_one({
            "rfq_id": rfq_id,
            "vendor_id": vendor["vendor_id"]
        })
        
        if not existing:
            await db.rfq_vendor_matches.insert_one(match_record)
            matches_created.append(match_record)
            
            # Also add to matched_vendors array in RFQ for backward compatibility
            match_info = {
                "vendor_id": vendor["vendor_id"],
                "company_name": vendor.get("company_name", "Unknown"),
                "suitability_score": 100,  # Manual match = 100% score
                "match_type": "manual",
                "matched_by": user["user_id"],
                "matched_at": now
            }
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$addToSet": {"matched_vendors": match_info}}
            )
    
    # Send notifications to vendors
    notified_vendors = 0
    for vendor in valid_vendors:
        try:
            # Send email notification
            await send_vendor_match_notification_email(vendor, rfq, buyer)
            
            # Send WhatsApp notification if configured
            if whatsapp_service.is_configured() and vendor.get("phone"):
                await send_vendor_match_whatsapp(vendor, rfq)
            
            # Create in-app notification
            notification = {
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "user_id": vendor.get("user_id"),
                "type": "rfq_match",
                "title": "New RFQ Match",
                "message": f"You have been matched to a new RFQ: {rfq.get('title', 'Untitled')}",
                "data": {
                    "rfq_id": rfq_id,
                    "rfq_title": rfq.get("title"),
                    "match_type": "manual"
                },
                "is_read": False,
                "created_at": now
            }
            await db.notifications.insert_one(notification)
            notified_vendors += 1
        except Exception as e:
            logger.error(f"Failed to notify vendor {vendor['vendor_id']}: {e}")
    
    # Send notification to buyer
    if buyer:
        try:
            await send_buyer_match_notification_email(buyer, rfq, len(valid_vendors))
            
            # Create in-app notification for buyer
            buyer_notification = {
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "user_id": buyer.get("user_id"),
                "type": "rfq_vendors_matched",
                "title": "Vendors Matched to Your RFQ",
                "message": f"Your RFQ '{rfq.get('title', 'Untitled')}' has been matched with {len(valid_vendors)} vendor(s). You will receive quotations soon.",
                "data": {
                    "rfq_id": rfq_id,
                    "vendor_count": len(valid_vendors)
                },
                "is_read": False,
                "created_at": now
            }
            await db.notifications.insert_one(buyer_notification)
        except Exception as e:
            logger.error(f"Failed to notify buyer: {e}")
    
    # Log activity
    activity_log = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "type": "rfq_vendors_matched",
        "action": "manual_match",
        "entity_type": "rfq",
        "entity_id": rfq_id,
        "user_id": user["user_id"],
        "user_name": user.get("name", user.get("email", "Unknown")),
        "details": {
            "rfq_title": rfq.get("title"),
            "vendor_count": len(valid_vendors),
            "vendor_ids": [v["vendor_id"] for v in valid_vendors],
            "vendor_names": [v.get("company_name", "Unknown") for v in valid_vendors]
        },
        "created_at": now
    }
    await db.activity_logs.insert_one(activity_log)
    
    logger.info(f"Manual match: {len(matches_created)} vendors matched to RFQ {rfq_id} by {user['user_id']}")
    
    return {
        "success": True,
        "matches_created": len(matches_created),
        "vendors_notified": notified_vendors,
        "message": f"Successfully matched {len(valid_vendors)} vendor(s) to RFQ"
    }


@api_router.get("/admin/rfq/{rfq_id}/matches")
async def admin_get_rfq_matches(rfq_id: str, user: dict = Depends(get_current_user)):
    """Get all vendors matched to an RFQ with their status"""
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "rfqs.view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    # Validate RFQ exists
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get all matches from rfq_vendor_matches collection
    matches = await db.rfq_vendor_matches.find({"rfq_id": rfq_id}, {"_id": 0}).to_list(100)
    
    # Enrich with vendor info and quote status
    enriched_matches = []
    for match in matches:
        vendor = await db.vendors.find_one({"vendor_id": match["vendor_id"]}, {"_id": 0})
        quote = await db.quotes.find_one({"rfq_id": rfq_id, "vendor_id": match["vendor_id"]}, {"_id": 0})
        
        enriched_match = {
            **match,
            "vendor_info": {
                "company_name": vendor.get("company_name") if vendor else "Unknown",
                "city": vendor.get("city") if vendor else "",
                "state": vendor.get("state") if vendor else "",
                "phone": vendor.get("phone") if vendor else "",
                "is_approved": vendor.get("is_approved") if vendor else False
            } if vendor else None,
            "has_quoted": quote is not None,
            "quote_info": {
                "quote_id": quote.get("quote_id"),
                "total_price": quote.get("total_price"),
                "status": quote.get("status"),
                "created_at": quote.get("created_at")
            } if quote else None
        }
        enriched_matches.append(enriched_match)
    
    # Also check matched_vendors from RFQ (for backward compatibility with auto-matches)
    matched_vendors = rfq.get("matched_vendors", [])
    existing_vendor_ids = {m["vendor_id"] for m in matches}
    
    for mv in matched_vendors:
        if mv.get("vendor_id") not in existing_vendor_ids:
            vendor = await db.vendors.find_one({"vendor_id": mv["vendor_id"]}, {"_id": 0})
            quote = await db.quotes.find_one({"rfq_id": rfq_id, "vendor_id": mv["vendor_id"]}, {"_id": 0})
            
            enriched_match = {
                "match_id": f"legacy_{mv['vendor_id']}",
                "rfq_id": rfq_id,
                "vendor_id": mv["vendor_id"],
                "status": "quoted" if quote else "matched",
                "match_type": mv.get("match_type", "auto"),
                "suitability_score": mv.get("suitability_score", 0),
                "created_at": mv.get("matched_at", rfq.get("created_at")),
                "vendor_info": {
                    "company_name": vendor.get("company_name") if vendor else mv.get("company_name", "Unknown"),
                    "city": vendor.get("city") if vendor else "",
                    "state": vendor.get("state") if vendor else "",
                    "phone": vendor.get("phone") if vendor else "",
                    "is_approved": vendor.get("is_approved") if vendor else False
                } if vendor else None,
                "has_quoted": quote is not None,
                "quote_info": {
                    "quote_id": quote.get("quote_id"),
                    "total_price": quote.get("total_price"),
                    "status": quote.get("status"),
                    "created_at": quote.get("created_at")
                } if quote else None
            }
            enriched_matches.append(enriched_match)
    
    return {
        "rfq_id": rfq_id,
        "matches": enriched_matches,
        "total_matched": len(enriched_matches),
        "total_quoted": len([m for m in enriched_matches if m.get("has_quoted")])
    }


@api_router.delete("/admin/rfq/{rfq_id}/match/{vendor_id}")
async def admin_remove_rfq_match(rfq_id: str, vendor_id: str, user: dict = Depends(get_current_user)):
    """Remove a vendor match from an RFQ"""
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "rfqs.match_vendors")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'rfqs.match_vendors' permission.")
    
    # Validate RFQ exists
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Remove from rfq_vendor_matches collection
    result = await db.rfq_vendor_matches.delete_one({"rfq_id": rfq_id, "vendor_id": vendor_id})
    
    # Also remove from matched_vendors array in RFQ
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$pull": {"matched_vendors": {"vendor_id": vendor_id}}}
    )
    
    # Log activity
    vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0, "company_name": 1})
    activity_log = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "type": "rfq_vendor_unmatched",
        "action": "unmatch",
        "entity_type": "rfq",
        "entity_id": rfq_id,
        "user_id": user["user_id"],
        "user_name": user.get("name", user.get("email", "Unknown")),
        "details": {
            "rfq_title": rfq.get("title"),
            "vendor_id": vendor_id,
            "vendor_name": vendor.get("company_name", "Unknown") if vendor else "Unknown"
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activity_logs.insert_one(activity_log)
    
    return {
        "success": True,
        "message": "Vendor match removed successfully"
    }


@api_router.put("/admin/rfq/{rfq_id}/match/{vendor_id}/status")
async def admin_update_match_status(
    rfq_id: str,
    vendor_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Update the status of a vendor match (e.g., viewed, responded)"""
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "rfqs.match_vendors")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    body = await request.json()
    new_status = body.get("status")
    
    if new_status not in ["matched", "viewed", "responded", "quoted"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be: matched, viewed, responded, quoted")
    
    result = await db.rfq_vendor_matches.update_one(
        {"rfq_id": rfq_id, "vendor_id": vendor_id},
        {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return {"success": True, "message": "Match status updated"}


@api_router.get("/admin/vendors/search")
async def admin_search_vendors_for_matching(
    user: dict = Depends(get_current_user),
    search: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    approved_only: bool = True,
    limit: int = 50
):
    """Search vendors for manual RFQ matching"""
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "rfqs.match_vendors")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    query = {}
    if approved_only:
        query["is_approved"] = True
    if search:
        query["$or"] = [
            {"company_name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if state:
        query["state"] = {"$regex": state, "$options": "i"}
    
    vendors = await db.vendors.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    # Enrich with machine info
    enriched_vendors = []
    for vendor in vendors:
        machines = await db.machines.find(
            {"vendor_id": vendor["vendor_id"]}, 
            {"_id": 0, "machine_category": 1, "machine_type": 1}
        ).to_list(50)
        
        # Filter by category if specified
        if category:
            matching_machines = [m for m in machines if category.lower() in (m.get("machine_category", "") or "").lower()]
            if not matching_machines:
                continue
        
        vendor["machines_count"] = len(machines)
        vendor["machine_categories"] = list(set(m.get("machine_category") for m in machines if m.get("machine_category")))
        vendor["machine_types"] = list(set(m.get("machine_type") for m in machines if m.get("machine_type")))[:10]
        enriched_vendors.append(vendor)
    
    return {
        "vendors": enriched_vendors,
        "total": len(enriched_vendors)
    }


# Helper functions for notifications
async def send_vendor_match_notification_email(vendor: dict, rfq: dict, buyer: dict):
    """Send email notification to vendor about new RFQ match"""
    try:
        from app.services.notification_service import notification_service
        
        vendor_user = await db.users.find_one({"user_id": vendor.get("user_id")}, {"_id": 0, "email": 1, "name": 1})
        if not vendor_user or not vendor_user.get("email"):
            return
        
        data = {
            "rfq_id": rfq.get("rfq_id"),
            "rfq_title": rfq.get("title", "New RFQ"),
            "material_type": rfq.get("material_type", "N/A"),
            "quantity": rfq.get("quantity", "As Required"),
            "tolerance": rfq.get("tolerance", "N/A"),
            "deadline": rfq.get("deadline", "As per RFQ"),
            "buyer_name": buyer.get("name", "Buyer") if buyer else "Buyer",
            "match_score": 100,
            "app_url": f"https://oemlinker.com/vendor/rfq/{rfq.get('rfq_id')}"
        }
        
        await notification_service.send_notification(
            channel="email",
            recipient=vendor_user["email"],
            notification_type="rfq_match",
            data=data
        )
    except Exception as e:
        logger.error(f"Failed to send vendor match email: {e}")


async def send_vendor_match_whatsapp(vendor: dict, rfq: dict):
    """Send WhatsApp notification to vendor about new RFQ match"""
    try:
        phone = vendor.get("phone", "").strip()
        if not phone:
            return
        
        company_name = vendor.get("company_name", "Partner")
        part_name = rfq.get("title", "New Part")[:50]
        quantity = str(rfq.get("quantity", "As Required"))
        
        # Generate magic link
        redirect_path = f"/vendor/rfq/{rfq['rfq_id']}"
        magic_link_result = await generate_magic_link_for_vendor(phone, redirect_path)
        
        if magic_link_result.get("success"):
            rfq_link = f"https://oemlinker.com/magic-login?token={magic_link_result['token']}"
        else:
            rfq_link = f"https://oemlinker.com/vendor/rfq/{rfq['rfq_id']}"
        
        message = f"""🔔 *New RFQ Match!*

Hello *{company_name}*,

You have been matched to a new RFQ opportunity.

📋 *{part_name}*
📦 Quantity: {quantity}
🎯 Match Score: 100%

👉 *View & Quote:*
{rfq_link}

_Team OEMLinker_"""
        
        await whatsapp_service.send_text_message(phone, message)
        logger.info(f"WhatsApp notification sent to vendor {vendor['vendor_id']}")
    except Exception as e:
        logger.error(f"Failed to send vendor match WhatsApp: {e}")


async def send_buyer_match_notification_email(buyer: dict, rfq: dict, vendor_count: int):
    """Send email notification to buyer about vendors matched to their RFQ"""
    try:
        from app.services.notification_service import notification_service
        
        if not buyer or not buyer.get("email"):
            return
        
        data = {
            "rfq_id": rfq.get("rfq_id"),
            "rfq_title": rfq.get("title", "Your RFQ"),
            "matched_count": vendor_count,
            "app_url": f"https://oemlinker.com/buyer/rfqs/{rfq.get('rfq_id')}"
        }
        
        await notification_service.send_notification(
            channel="email",
            recipient=buyer["email"],
            notification_type="rfq_vendor_matched",
            data=data
        )
    except Exception as e:
        logger.error(f"Failed to send buyer match email: {e}")


# ============== ADMIN - QUOTE MANAGEMENT ==============

@api_router.get("/admin/quotes")
async def admin_list_quotes(user: dict = Depends(get_current_user), status: Optional[str] = None):
    """List all quotes"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    quotes = await db.quotes.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Enrich with RFQ and vendor info
    for quote in quotes:
        rfq = await db.rfqs.find_one({"rfq_id": quote["rfq_id"]}, {"_id": 0, "title": 1})
        vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0, "company_name": 1})
        quote["rfq_info"] = rfq
        quote["vendor_info"] = vendor
    
    return quotes

@api_router.put("/admin/quotes/{quote_id}")
async def admin_update_quote(quote_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update quote details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    allowed_fields = ["price", "lead_time_days", "status", "notes"]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    
    result = await db.quotes.update_one({"quote_id": quote_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"message": "Quote updated successfully"}

@api_router.delete("/admin/quotes/{quote_id}")
async def admin_delete_quote(quote_id: str, user: dict = Depends(get_current_user)):
    """Delete a quote"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.quotes.delete_one({"quote_id": quote_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"message": "Quote deleted successfully"}

# ============== ADMIN - ORDER MANAGEMENT ==============

@api_router.get("/admin/orders")
async def admin_list_orders(user: dict = Depends(get_current_user), status: Optional[str] = None):
    """List all orders"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Enrich with buyer and vendor info
    for order in orders:
        buyer = await db.users.find_one({"user_id": order["buyer_id"]}, {"_id": 0, "name": 1, "email": 1})
        vendor = await db.vendors.find_one({"vendor_id": order["vendor_id"]}, {"_id": 0, "company_name": 1})
        rfq = await db.rfqs.find_one({"rfq_id": order["rfq_id"]}, {"_id": 0, "title": 1})
        order["buyer_info"] = buyer
        order["vendor_info"] = vendor
        order["rfq_info"] = rfq
    
    return orders

@api_router.put("/admin/orders/{order_id}")
async def admin_update_order(order_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update order details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    allowed_fields = ["status", "payment_status", "total_amount"]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Add tracking update if status changed
    if "status" in update_data:
        await db.orders.update_one(
            {"order_id": order_id},
            {"$push": {"tracking_updates": {
                "status": update_data["status"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": f"Status updated by admin"
            }}}
        )
    
    result = await db.orders.update_one({"order_id": order_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Order updated successfully"}

@api_router.delete("/admin/orders/{order_id}")
async def admin_delete_order(order_id: str, user: dict = Depends(get_current_user)):
    """Delete an order"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.orders.delete_one({"order_id": order_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Order deleted successfully"}

# ============== ADMIN - DRAWING MANAGEMENT ==============

@api_router.get("/admin/drawings")
async def admin_list_drawings(user: dict = Depends(get_current_user)):
    """List all drawings (without file data)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    drawings = await db.drawings.find({}, {"_id": 0, "file_data": 0}).sort("created_at", -1).to_list(200)
    
    # Enrich with RFQ info
    for drawing in drawings:
        rfq = await db.rfqs.find_one({"rfq_id": drawing["rfq_id"]}, {"_id": 0, "title": 1})
        drawing["rfq_info"] = rfq
    
    return drawings

@api_router.get("/admin/drawings/{drawing_id}")
async def admin_get_drawing(drawing_id: str, user: dict = Depends(get_current_user)):
    """Get drawing details including file data"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
    return drawing

@api_router.delete("/admin/drawings/{drawing_id}")
async def admin_delete_drawing(drawing_id: str, user: dict = Depends(get_current_user)):
    """Delete a drawing"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Remove from RFQ drawing_ids
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if drawing:
        await db.rfqs.update_one(
            {"rfq_id": drawing["rfq_id"]},
            {"$pull": {"drawing_ids": drawing_id}}
        )
    
    result = await db.drawings.delete_one({"drawing_id": drawing_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
    return {"message": "Drawing deleted successfully"}

# ============== ADMIN - NDA MANAGEMENT ==============

class NDAStatus:
    DRAFT = "draft"
    SENT = "sent"
    SIGNED = "signed"
    EXPIRED = "expired"
    REJECTED = "rejected"

class NDACreate(BaseModel):
    buyer_id: str
    vendor_id: str
    rfq_id: Optional[str] = None
    title: str
    content: str
    valid_until: Optional[str] = None

@api_router.post("/admin/ndas")
async def admin_create_nda(nda: NDACreate, user: dict = Depends(get_current_user)):
    """Create a new NDA"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    nda_id = f"nda_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    nda_doc = {
        "nda_id": nda_id,
        "buyer_id": nda.buyer_id,
        "vendor_id": nda.vendor_id,
        "rfq_id": nda.rfq_id,
        "title": nda.title,
        "content": nda.content,
        "status": NDAStatus.DRAFT,
        "valid_until": nda.valid_until or (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "buyer_signed": False,
        "buyer_signed_at": None,
        "vendor_signed": False,
        "vendor_signed_at": None,
        "created_by": user["user_id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.ndas.insert_one(nda_doc)
    return {"nda_id": nda_id, "message": "NDA created successfully"}

@api_router.get("/admin/ndas")
async def admin_list_ndas(user: dict = Depends(get_current_user), status: Optional[str] = None):
    """List all NDAs"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    ndas = await db.ndas.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Enrich with buyer and vendor info
    for nda in ndas:
        buyer = await db.users.find_one({"user_id": nda["buyer_id"]}, {"_id": 0, "name": 1, "email": 1})
        vendor = await db.vendors.find_one({"vendor_id": nda["vendor_id"]}, {"_id": 0, "company_name": 1})
        nda["buyer_info"] = buyer
        nda["vendor_info"] = vendor
    
    return ndas

@api_router.get("/admin/ndas/{nda_id}")
async def admin_get_nda(nda_id: str, user: dict = Depends(get_current_user)):
    """Get NDA details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    nda = await db.ndas.find_one({"nda_id": nda_id}, {"_id": 0})
    if not nda:
        raise HTTPException(status_code=404, detail="NDA not found")
    
    buyer = await db.users.find_one({"user_id": nda["buyer_id"]}, {"_id": 0, "name": 1, "email": 1})
    vendor = await db.vendors.find_one({"vendor_id": nda["vendor_id"]}, {"_id": 0, "company_name": 1})
    
    return {**nda, "buyer_info": buyer, "vendor_info": vendor}

@api_router.put("/admin/ndas/{nda_id}")
async def admin_update_nda(nda_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update NDA details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    allowed_fields = ["title", "content", "status", "valid_until"]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.ndas.update_one({"nda_id": nda_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="NDA not found")
    
    return {"message": "NDA updated successfully"}

@api_router.post("/admin/ndas/{nda_id}/send")
async def admin_send_nda(nda_id: str, user: dict = Depends(get_current_user)):
    """Send NDA to parties for signing"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.ndas.update_one(
        {"nda_id": nda_id},
        {"$set": {"status": NDAStatus.SENT, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="NDA not found")
    
    return {"message": "NDA sent for signing"}

@api_router.delete("/admin/ndas/{nda_id}")
async def admin_delete_nda(nda_id: str, user: dict = Depends(get_current_user)):
    """Delete an NDA"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.ndas.delete_one({"nda_id": nda_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="NDA not found")
    
    return {"message": "NDA deleted successfully"}

# ============== NDA ROUTES (for buyers/vendors) ==============

@api_router.get("/ndas")
async def list_my_ndas(user: dict = Depends(get_current_user)):
    """Get NDAs for current user"""
    query = {"$or": [{"buyer_id": user["user_id"]}]}
    
    # If vendor, also include vendor NDAs
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if vendor:
        query["$or"].append({"vendor_id": vendor["vendor_id"]})
    
    ndas = await db.ndas.find(query, {"_id": 0}).to_list(50)
    return ndas

@api_router.post("/ndas/{nda_id}/sign")
async def sign_nda(nda_id: str, user: dict = Depends(get_current_user)):
    """Sign an NDA"""
    nda = await db.ndas.find_one({"nda_id": nda_id}, {"_id": 0})
    if not nda:
        raise HTTPException(status_code=404, detail="NDA not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {"updated_at": now}
    
    # Check if user is buyer or vendor
    if nda["buyer_id"] == user["user_id"]:
        update_data["buyer_signed"] = True
        update_data["buyer_signed_at"] = now
    else:
        vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if vendor and vendor["vendor_id"] == nda["vendor_id"]:
            update_data["vendor_signed"] = True
            update_data["vendor_signed_at"] = now
        else:
            raise HTTPException(status_code=403, detail="Not authorized to sign this NDA")
    
    await db.ndas.update_one({"nda_id": nda_id}, {"$set": update_data})
    
    # Check if both parties signed
    updated_nda = await db.ndas.find_one({"nda_id": nda_id}, {"_id": 0})
    if updated_nda["buyer_signed"] and updated_nda["vendor_signed"]:
        await db.ndas.update_one({"nda_id": nda_id}, {"$set": {"status": NDAStatus.SIGNED}})
    
    return {"message": "NDA signed successfully"}

# ============== ADMIN - VENDOR MANAGEMENT (Extended) ==============

@api_router.get("/admin/vendors")
async def admin_list_vendors(user: dict = Depends(get_current_user), approved: Optional[bool] = None):
    """List all vendors"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if approved is not None:
        query["is_approved"] = approved
    
    vendors = await db.vendors.find(query, {"_id": 0}).to_list(200)
    
    # Enrich with user info and machine count
    for vendor in vendors:
        vendor_user = await db.users.find_one({"user_id": vendor["user_id"]}, {"_id": 0, "email": 1, "name": 1})
        machine_count = await db.machines.count_documents({"vendor_id": vendor["vendor_id"]})
        vendor["user_info"] = vendor_user
        vendor["machine_count"] = machine_count
    
    return vendors

@api_router.get("/admin/vendors/search-by-machines")
async def search_vendors_by_machines(
    user: dict = Depends(get_current_user),
    machine_category: Optional[str] = None,
    machine_type: Optional[str] = None,
    min_x: Optional[float] = None,
    min_y: Optional[float] = None,
    min_z: Optional[float] = None,
    min_diameter: Optional[float] = None,
    min_length: Optional[float] = None,
    min_weight: Optional[float] = None,
    min_tonnage: Optional[float] = None,
    material: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    approved_only: bool = True
):
    """
    Search vendors by their machine capabilities.
    Returns vendors that have machines matching the specified criteria.
    Requires 'vendors.search_machines' permission.
    """
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        # Check for specific permission via custom role
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "vendors.search_machines")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'vendors.search_machines' permission.")
    
    # Build machine query
    machine_query = {"is_active": True}
    
    if machine_category:
        machine_query["machine_category"] = machine_category
    if machine_type:
        machine_query["machine_type"] = machine_type
    
    # Dimension filters
    if min_x:
        machine_query["max_x"] = {"$gte": min_x}
    if min_y:
        machine_query["max_y"] = {"$gte": min_y}
    if min_z:
        machine_query["max_z"] = {"$gte": min_z}
    if min_diameter:
        machine_query["max_diameter"] = {"$gte": min_diameter}
    if min_length:
        machine_query["max_length"] = {"$gte": min_length}
    if min_weight:
        machine_query["max_weight"] = {"$gte": min_weight}
    if min_tonnage:
        machine_query["tonnage"] = {"$gte": min_tonnage}
    
    # Material filter (check if material is in the materials array)
    if material:
        machine_query["$or"] = [
            {"materials": {"$regex": material, "$options": "i"}},
            {"materials_supported": {"$regex": material, "$options": "i"}}
        ]
    
    # Find machines matching criteria
    matching_machines = await db.machines.find(machine_query, {"_id": 0}).to_list(1000)
    
    # Get unique vendor IDs from matching machines
    vendor_ids = list(set(m["vendor_id"] for m in matching_machines))
    
    if not vendor_ids:
        return {"vendors": [], "total": 0, "machines_found": 0}
    
    # Build vendor query
    vendor_query = {"vendor_id": {"$in": vendor_ids}}
    if approved_only:
        vendor_query["is_approved"] = True
    if city:
        vendor_query["city"] = {"$regex": city, "$options": "i"}
    if state:
        vendor_query["state"] = {"$regex": state, "$options": "i"}
    
    # Fetch vendors
    vendors = await db.vendors.find(vendor_query, {"_id": 0}).to_list(200)
    
    # Enrich vendors with machine details and user info
    result_vendors = []
    for vendor in vendors:
        # Get user info
        vendor_user = await db.users.find_one({"user_id": vendor["user_id"]}, {"_id": 0, "email": 1, "name": 1})
        vendor["user_info"] = vendor_user
        
        # Get matching machines for this vendor
        vendor_machines = [m for m in matching_machines if m["vendor_id"] == vendor["vendor_id"]]
        vendor["matching_machines"] = vendor_machines
        vendor["matching_machine_count"] = len(vendor_machines)
        
        # Total machine count
        total_machines = await db.machines.count_documents({"vendor_id": vendor["vendor_id"]})
        vendor["total_machine_count"] = total_machines
        
        result_vendors.append(vendor)
    
    # Sort by matching machine count (most capable first)
    result_vendors.sort(key=lambda v: v["matching_machine_count"], reverse=True)
    
    return {
        "vendors": result_vendors,
        "total": len(result_vendors),
        "machines_found": len(matching_machines),
        "search_criteria": {
            "machine_category": machine_category,
            "machine_type": machine_type,
            "min_dimensions": {"x": min_x, "y": min_y, "z": min_z, "diameter": min_diameter, "length": min_length},
            "material": material,
            "location": {"city": city, "state": state}
        }
    }

@api_router.put("/admin/vendors/{vendor_id}")
async def admin_update_vendor(vendor_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update vendor details"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    allowed_fields = ["company_name", "is_approved", "rating", "description", "certifications", "industries"]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    
    result = await db.vendors.update_one({"vendor_id": vendor_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return {"message": "Vendor updated successfully"}

@api_router.post("/admin/vendors/{vendor_id}/reject")
async def admin_reject_vendor(vendor_id: str, user: dict = Depends(get_current_user)):
    """Reject/unapprove a vendor"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.vendors.update_one(
        {"vendor_id": vendor_id},
        {"$set": {"is_approved": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return {"message": "Vendor rejected"}

# ============== ADMIN - VENDOR PROFILE MANAGEMENT ==============

@api_router.get("/admin/vendors/{vendor_id}/full")
async def admin_get_vendor_full_profile(vendor_id: str, user: dict = Depends(get_current_user)):
    """Get complete vendor profile with all details for admin editing"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get user info
    vendor_user = await db.users.find_one({"user_id": vendor["user_id"]}, {"_id": 0, "password_hash": 0})
    
    # Get all machines
    machines = await db.machines.find({"vendor_id": vendor_id}, {"_id": 0}).to_list(100)
    
    # Get stats
    quotes = await db.quotes.find({"vendor_id": vendor_id}, {"_id": 0}).to_list(100)
    orders = await db.orders.find({"vendor_id": vendor_id}, {"_id": 0}).to_list(100)
    
    return {
        "vendor": vendor,
        "user_info": vendor_user,
        "machines": machines,
        "stats": {
            "total_machines": len(machines),
            "total_quotes": len(quotes),
            "accepted_quotes": len([q for q in quotes if q.get("status") == "accepted"]),
            "total_orders": len(orders),
            "completed_orders": len([o for o in orders if o.get("status") == "completed"]),
            "total_revenue": sum(o.get("total_amount", 0) for o in orders if o.get("payment_status") == "paid")
        }
    }

@api_router.put("/admin/vendors/{vendor_id}/profile")
async def admin_update_vendor_profile(vendor_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update vendor profile details (admin)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    
    # Allowed vendor fields
    vendor_fields = ["company_name", "description", "phone", "website", "address", "city", "state", "pincode", "country", 
                     "certifications", "industries", "is_approved", "rating", "min_order_value", "lead_time_days"]
    vendor_update = {k: v for k, v in body.items() if k in vendor_fields}
    
    if vendor_update:
        result = await db.vendors.update_one({"vendor_id": vendor_id}, {"$set": vendor_update})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Vendor not found")
    
    return {"message": "Vendor profile updated successfully"}

# ============== ADMIN - MACHINE MANAGEMENT ==============

@api_router.get("/admin/machines")
async def admin_list_all_machines(user: dict = Depends(get_current_user), vendor_id: Optional[str] = None):
    """List all machines, optionally filtered by vendor (admin or users with machines.view permission)"""
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'machines.view' permission.")
    
    query = {}
    if vendor_id:
        query["vendor_id"] = vendor_id
    
    machines = await db.machines.find(query, {"_id": 0}).to_list(500)
    
    # Enrich with vendor info
    for machine in machines:
        vendor = await db.vendors.find_one({"vendor_id": machine["vendor_id"]}, {"_id": 0, "company_name": 1})
        machine["vendor_name"] = vendor.get("company_name") if vendor else "Unknown"
    
    return machines

@api_router.get("/machine-categories")
async def get_machine_categories():
    """Get machine categories with their specific dimension fields"""
    categories = {
        "CNC Turning/Lathe": {
            "types": ["CNC Lathe", "CNC Turning", "Swiss Lathe", "CNC Turn-Mill"],
            "dimension_fields": [
                {"key": "max_length", "label": "Max Turning Length (mm)", "type": "number"},
                {"key": "max_diameter", "label": "Max Turning Diameter (mm)", "type": "number"},
                {"key": "max_swing", "label": "Max Swing Over Bed (mm)", "type": "number"}
            ]
        },
        "VTL (Vertical Turret Lathe)": {
            "types": ["VTL", "Vertical Turret Lathe", "CNC VTL", "Double Column VTL"],
            "dimension_fields": [
                {"key": "max_diameter", "label": "Max Turning Diameter (mm)", "type": "number"},
                {"key": "max_length", "label": "Max Turning Height (mm)", "type": "number"},
                {"key": "table_diameter", "label": "Table Diameter (mm)", "type": "number"},
                {"key": "max_weight", "label": "Max Workpiece Weight (kg)", "type": "number"}
            ]
        },
        "VMC (Vertical Machining Center)": {
            "types": ["VMC", "CNC VMC", "High Speed VMC", "Heavy Duty VMC", "Double Column VMC"],
            "dimension_fields": [
                {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
                {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
                {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
                {"key": "table_size_x", "label": "Table Size X (mm)", "type": "number"},
                {"key": "table_size_y", "label": "Table Size Y (mm)", "type": "number"}
            ]
        },
        "HMC (Horizontal Machining Center)": {
            "types": ["HMC", "CNC HMC", "Pallet HMC", "High Speed HMC"],
            "dimension_fields": [
                {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
                {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
                {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
                {"key": "pallet_size", "label": "Pallet Size (mm)", "type": "number"}
            ]
        },
        "5-Axis Machining": {
            "types": ["5-Axis VMC", "5-Axis HMC", "5-Axis Mill-Turn", "5-Axis Gantry"],
            "dimension_fields": [
                {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
                {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
                {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
                {"key": "max_diameter", "label": "Max Part Diameter (mm)", "type": "number"},
                {"key": "a_axis_range", "label": "A-Axis Range (°)", "type": "number"},
                {"key": "c_axis_range", "label": "C-Axis Range (°)", "type": "number"}
            ]
        },
        "Conventional Lathe": {
            "types": ["Engine Lathe", "Turret Lathe", "Capstan Lathe", "Gap Bed Lathe", "Heavy Duty Lathe"],
            "dimension_fields": [
                {"key": "max_length", "label": "Center Distance (mm)", "type": "number"},
                {"key": "max_diameter", "label": "Swing Over Bed (mm)", "type": "number"},
                {"key": "spindle_bore", "label": "Spindle Bore (mm)", "type": "number"}
            ]
        },
        "Conventional Milling": {
            "types": ["Universal Milling", "Vertical Milling", "Horizontal Milling", "Knee Mill", "Bed Mill", "Ram Turret Mill"],
            "dimension_fields": [
                {"key": "max_x", "label": "Table Travel X (mm)", "type": "number"},
                {"key": "max_y", "label": "Table Travel Y (mm)", "type": "number"},
                {"key": "max_z", "label": "Head Travel Z (mm)", "type": "number"},
                {"key": "table_size_x", "label": "Table Size X (mm)", "type": "number"},
                {"key": "table_size_y", "label": "Table Size Y (mm)", "type": "number"}
            ]
        },
        "Boring Machine": {
            "types": ["Horizontal Boring Mill", "Vertical Boring Mill", "Jig Boring", "Line Boring", "CNC Boring Mill", "Floor Boring"],
            "dimension_fields": [
                {"key": "bore_diameter", "label": "Max Spindle Diameter (mm)", "type": "number"},
                {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
                {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
                {"key": "max_z", "label": "Z-Axis/Spindle Travel (mm)", "type": "number"}
            ]
        },
        "Shaping Machine": {
            "types": ["Shaper", "Planer", "Slotter", "CNC Shaper"],
            "dimension_fields": [
                {"key": "max_stroke", "label": "Max Stroke Length (mm)", "type": "number"},
                {"key": "max_x", "label": "Table Travel X (mm)", "type": "number"},
                {"key": "max_y", "label": "Table Travel Y (mm)", "type": "number"},
                {"key": "table_size_x", "label": "Table Size X (mm)", "type": "number"}
            ]
        },
        "Gear Manufacturing": {
            "types": ["Gear Hobbing", "Gear Shaping", "Gear Grinding", "Gear Shaving", "Bevel Gear Generator", "CNC Gear Hobbing"],
            "dimension_fields": [
                {"key": "max_diameter", "label": "Max Gear Diameter (mm)", "type": "number"},
                {"key": "max_module", "label": "Max Module (mm)", "type": "number"},
                {"key": "max_length", "label": "Max Face Width (mm)", "type": "number"},
                {"key": "min_teeth", "label": "Min No. of Teeth", "type": "number"}
            ]
        },
        "Grinding": {
            "types": ["Surface Grinder", "Cylindrical Grinder", "Centerless Grinder", "ID Grinder", "Tool & Cutter Grinder", "CNC Grinding"],
            "dimension_fields": [
                {"key": "max_x", "label": "Table Travel/Length (mm)", "type": "number"},
                {"key": "max_y", "label": "Table Width (mm)", "type": "number"},
                {"key": "max_diameter", "label": "Max Grinding Diameter (mm)", "type": "number"},
                {"key": "max_length", "label": "Max Grinding Length (mm)", "type": "number"}
            ]
        },
        "EDM": {
            "types": ["Wire EDM", "Sinker EDM", "Hole Drilling EDM", "CNC EDM"],
            "dimension_fields": [
                {"key": "max_x", "label": "X-Axis Travel (mm)", "type": "number"},
                {"key": "max_y", "label": "Y-Axis Travel (mm)", "type": "number"},
                {"key": "max_z", "label": "Z-Axis Travel (mm)", "type": "number"},
                {"key": "max_taper_angle", "label": "Max Taper Angle (°)", "type": "number"},
                {"key": "max_thickness", "label": "Max Workpiece Thickness (mm)", "type": "number"}
            ]
        },
        "Drilling Machine": {
            "types": ["Radial Drill", "Pillar Drill", "Bench Drill", "Gang Drill", "CNC Drilling", "Deep Hole Drilling"],
            "dimension_fields": [
                {"key": "max_diameter", "label": "Max Drilling Diameter (mm)", "type": "number"},
                {"key": "max_depth", "label": "Max Drilling Depth (mm)", "type": "number"},
                {"key": "spindle_travel", "label": "Spindle Travel (mm)", "type": "number"},
                {"key": "arm_length", "label": "Radial Arm Length (mm)", "type": "number"}
            ]
        },
        "Laser Cutting": {
            "types": ["CO2 Laser", "Fiber Laser", "Tube Laser", "3D Laser Cutting"],
            "dimension_fields": [
                {"key": "max_x", "label": "Cutting Area X (mm)", "type": "number"},
                {"key": "max_y", "label": "Cutting Area Y (mm)", "type": "number"},
                {"key": "max_thickness", "label": "Max Cutting Thickness (mm)", "type": "number"},
                {"key": "laser_power", "label": "Laser Power (kW)", "type": "number"}
            ]
        },
        "Plasma/Waterjet Cutting": {
            "types": ["Plasma Cutting", "Waterjet Cutting", "CNC Plasma", "Abrasive Waterjet"],
            "dimension_fields": [
                {"key": "max_x", "label": "Cutting Area X (mm)", "type": "number"},
                {"key": "max_y", "label": "Cutting Area Y (mm)", "type": "number"},
                {"key": "max_thickness", "label": "Max Cutting Thickness (mm)", "type": "number"}
            ]
        },
        "Sheet Metal/Press": {
            "types": ["Press Brake", "Hydraulic Press", "Mechanical Press", "Punch Press", "Shearing Machine", "Roll Forming"],
            "dimension_fields": [
                {"key": "max_length", "label": "Bed Length (mm)", "type": "number"},
                {"key": "max_thickness", "label": "Max Sheet Thickness (mm)", "type": "number"},
                {"key": "tonnage", "label": "Tonnage/Press Force (ton)", "type": "number"},
                {"key": "stroke", "label": "Stroke (mm)", "type": "number"}
            ]
        },
        "Welding": {
            "types": ["MIG Welding", "TIG Welding", "ARC Welding", "Spot Welding", "Seam Welding", "Laser Welding", "Robot Welding", "Submerged Arc Welding"],
            "dimension_fields": [
                {"key": "max_thickness", "label": "Max Weld Thickness (mm)", "type": "number"},
                {"key": "max_length", "label": "Max Weld Length (mm)", "type": "number"},
                {"key": "amperage", "label": "Max Amperage (A)", "type": "number"}
            ]
        },
        "Heat Treatment": {
            "types": ["Furnace", "Induction Hardening", "Case Hardening", "Annealing", "Quenching", "Tempering"],
            "dimension_fields": [
                {"key": "max_x", "label": "Chamber Length (mm)", "type": "number"},
                {"key": "max_y", "label": "Chamber Width (mm)", "type": "number"},
                {"key": "max_z", "label": "Chamber Height (mm)", "type": "number"},
                {"key": "max_temp", "label": "Max Temperature (°C)", "type": "number"}
            ]
        },
        "Surface Treatment": {
            "types": ["Shot Blasting", "Sand Blasting", "Electroplating", "Anodizing", "Powder Coating", "Painting"],
            "dimension_fields": [
                {"key": "max_x", "label": "Max Part Length (mm)", "type": "number"},
                {"key": "max_y", "label": "Max Part Width (mm)", "type": "number"},
                {"key": "max_z", "label": "Max Part Height (mm)", "type": "number"},
                {"key": "max_weight", "label": "Max Part Weight (kg)", "type": "number"}
            ]
        },
        "Inspection/CMM": {
            "types": ["CMM", "Vision System", "Profile Projector", "Roughness Tester", "Hardness Tester", "3D Scanner"],
            "dimension_fields": [
                {"key": "max_x", "label": "Measuring Range X (mm)", "type": "number"},
                {"key": "max_y", "label": "Measuring Range Y (mm)", "type": "number"},
                {"key": "max_z", "label": "Measuring Range Z (mm)", "type": "number"},
                {"key": "accuracy", "label": "Accuracy (μm)", "type": "number"}
            ]
        },
        "Additive Manufacturing": {
            "types": ["FDM", "SLA", "SLS", "DMLS", "SLM", "Binder Jetting", "Metal 3D Printing"],
            "dimension_fields": [
                {"key": "max_x", "label": "Build Volume X (mm)", "type": "number"},
                {"key": "max_y", "label": "Build Volume Y (mm)", "type": "number"},
                {"key": "max_z", "label": "Build Volume Z (mm)", "type": "number"},
                {"key": "layer_thickness", "label": "Min Layer Thickness (μm)", "type": "number"}
            ]
        },
        "Casting": {
            "types": ["Sand Casting", "Investment Casting", "Die Casting", "Gravity Die Casting", "Pressure Die Casting", "Centrifugal Casting", "Shell Moulding", "Lost Wax Casting", "Continuous Casting"],
            "dimension_fields": [
                {"key": "max_weight", "label": "Max Casting Weight (kg)", "type": "number"},
                {"key": "max_x", "label": "Max Casting Length (mm)", "type": "number"},
                {"key": "max_y", "label": "Max Casting Width (mm)", "type": "number"},
                {"key": "max_z", "label": "Max Casting Height (mm)", "type": "number"},
                {"key": "min_thickness", "label": "Min Wall Thickness (mm)", "type": "number"}
            ]
        },
        "Forging": {
            "types": ["Open Die Forging", "Closed Die Forging", "Drop Forging", "Press Forging", "Roll Forging", "Upset Forging", "Ring Rolling", "Cold Forging", "Hot Forging"],
            "dimension_fields": [
                {"key": "max_weight", "label": "Max Forging Weight (kg)", "type": "number"},
                {"key": "tonnage", "label": "Press/Hammer Tonnage (ton)", "type": "number"},
                {"key": "max_diameter", "label": "Max Forging Diameter (mm)", "type": "number"},
                {"key": "max_length", "label": "Max Forging Length (mm)", "type": "number"}
            ]
        }
    }
    return categories

@api_router.post("/admin/machines")
async def admin_create_machine(request: Request, user: dict = Depends(get_current_user)):
    """Create a machine for any vendor (admin or users with machines.create permission)"""
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.create")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'machines.create' permission.")
    
    body = await request.json()
    vendor_id = body.get("vendor_id")
    
    if not vendor_id:
        raise HTTPException(status_code=400, detail="vendor_id is required")
    
    # Validate required fields
    machine_category = body.get("machine_category", "")
    if not machine_category:
        raise HTTPException(status_code=400, detail="machine_category is required")
    
    vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    machine_id = f"machine_{uuid.uuid4().hex[:12]}"
    machine_doc = {
        "machine_id": machine_id,
        "vendor_id": vendor_id,
        "name": body.get("name", ""),
        "machine_type": body.get("machine_type", ""),
        "machine_category": machine_category,
        "brand": body.get("brand", ""),
        "model": body.get("model", ""),
        "year_purchased": body.get("year_purchased"),
        "tolerance": body.get("tolerance", 0.01),
        # Standard dimensions
        "max_x": body.get("max_x", 0),
        "max_y": body.get("max_y", 0),
        "max_z": body.get("max_z", 0),
        "max_diameter": body.get("max_diameter", 0),
        "max_length": body.get("max_length", 0),
        "max_swing": body.get("max_swing", 0),
        # Boring/Drilling specific
        "bore_diameter": body.get("bore_diameter", 0),
        "outer_diameter": body.get("outer_diameter", 0),
        "spindle_bore": body.get("spindle_bore", 0),
        "spindle_travel": body.get("spindle_travel", 0),
        "arm_length": body.get("arm_length", 0),
        "max_depth": body.get("max_depth", 0),
        # VTL/Table specific
        "table_diameter": body.get("table_diameter", 0),
        "table_size_x": body.get("table_size_x", 0),
        "table_size_y": body.get("table_size_y", 0),
        "pallet_size": body.get("pallet_size", 0),
        "max_weight": body.get("max_weight", 0),
        # Shaping specific
        "max_stroke": body.get("max_stroke", 0),
        "stroke": body.get("stroke", 0),
        # Gear specific
        "max_module": body.get("max_module", 0),
        "min_teeth": body.get("min_teeth", 0),
        # 5-Axis specific
        "a_axis_range": body.get("a_axis_range", 0),
        "c_axis_range": body.get("c_axis_range", 0),
        # Sheet Metal/Press specific
        "tonnage": body.get("tonnage", 0),
        "max_thickness": body.get("max_thickness", 0),
        # Laser specific
        "laser_power": body.get("laser_power", 0),
        # Welding specific
        "amperage": body.get("amperage", 0),
        # Heat Treatment specific
        "max_temp": body.get("max_temp", 0),
        # Inspection specific
        "accuracy": body.get("accuracy", 0),
        # Additive specific
        "layer_thickness": body.get("layer_thickness", 0),
        # EDM specific
        "max_taper_angle": body.get("max_taper_angle", 0),
        # Casting specific
        "min_thickness": body.get("min_thickness", 0),
        # General
        "images": [],
        "materials": body.get("materials", []),
        "materials_supported": body.get("materials_supported", []),
        "is_active": body.get("is_active", True),
        "created_by": user["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.machines.insert_one(machine_doc)
    
    # Log activity
    activity_log = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "type": "machine_created",
        "action": "create",
        "entity_type": "machine",
        "entity_id": machine_id,
        "vendor_id": vendor_id,
        "user_id": user["user_id"],
        "user_name": user.get("name", user.get("email", "Unknown")),
        "details": {
            "machine_name": body.get("name", "") or f"{body.get('brand', '')} {body.get('model', '')}".strip(),
            "machine_category": machine_category,
            "machine_type": body.get("machine_type", ""),
            "vendor_name": vendor.get("company_name", "Unknown")
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activity_logs.insert_one(activity_log)
    
    logger.info(f"Machine created: {machine_id} for vendor {vendor_id} by user {user['user_id']}")
    
    return {"machine_id": machine_id, "message": "Machine created successfully"}

@api_router.get("/admin/machines/{machine_id}")
async def admin_get_machine(machine_id: str, user: dict = Depends(get_current_user)):
    """Get machine details (admin or users with machines.view permission)"""
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'machines.view' permission.")
    
    machine = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get vendor info
    vendor = await db.vendors.find_one({"vendor_id": machine["vendor_id"]}, {"_id": 0, "company_name": 1})
    machine["vendor_name"] = vendor.get("company_name") if vendor else "Unknown"
    
    return machine

@api_router.put("/admin/machines/{machine_id}")
async def admin_update_machine(machine_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update any machine (admin or users with machines.edit permission)"""
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.edit")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'machines.edit' permission.")
    
    body = await request.json()
    
    # Allowed fields - includes all machine-specific dimension fields
    allowed_fields = [
        "name", "machine_type", "machine_category", "brand", "model", "year_purchased", "tolerance",
        # Standard dimensions
        "max_x", "max_y", "max_z", "max_diameter", "max_length", "max_swing",
        # Boring/Drilling
        "bore_diameter", "outer_diameter", "spindle_bore", "spindle_travel", "arm_length", "max_depth",
        # VTL/Table
        "table_diameter", "table_size_x", "table_size_y", "pallet_size", "max_weight",
        # Shaping
        "max_stroke", "stroke",
        # Gear
        "max_module", "min_teeth",
        # 5-Axis
        "a_axis_range", "c_axis_range",
        # Sheet Metal/Press
        "tonnage", "max_thickness",
        # Laser
        "laser_power",
        # Welding
        "amperage",
        # Heat Treatment
        "max_temp",
        # Inspection
        "accuracy",
        # Additive
        "layer_thickness",
        # EDM
        "max_taper_angle",
        # General
        "materials", "materials_supported", "is_active"
    ]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # Get machine for logging
    machine = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = user["user_id"]
    
    result = await db.machines.update_one({"machine_id": machine_id}, {"$set": update_data})
    
    # Log activity
    vendor = await db.vendors.find_one({"vendor_id": machine.get("vendor_id")}, {"_id": 0, "company_name": 1})
    activity_log = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "type": "machine_updated",
        "action": "update",
        "entity_type": "machine",
        "entity_id": machine_id,
        "vendor_id": machine.get("vendor_id"),
        "user_id": user["user_id"],
        "user_name": user.get("name", user.get("email", "Unknown")),
        "details": {
            "machine_name": machine.get("name", "") or f"{machine.get('brand', '')} {machine.get('model', '')}".strip(),
            "updated_fields": list(update_data.keys()),
            "vendor_name": vendor.get("company_name", "Unknown") if vendor else "Unknown"
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activity_logs.insert_one(activity_log)
    
    logger.info(f"Machine updated: {machine_id} by user {user['user_id']}")
    
    return {"message": "Machine updated successfully"}

@api_router.delete("/admin/machines/{machine_id}")
async def admin_delete_machine(machine_id: str, user: dict = Depends(get_current_user)):
    """Delete any machine (admin or users with machines.delete permission)"""
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.delete")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'machines.delete' permission.")
    
    # Get machine for logging before deleting
    machine = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    result = await db.machines.delete_one({"machine_id": machine_id})
    
    # Log activity
    vendor = await db.vendors.find_one({"vendor_id": machine.get("vendor_id")}, {"_id": 0, "company_name": 1})
    activity_log = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "type": "machine_deleted",
        "action": "delete",
        "entity_type": "machine",
        "entity_id": machine_id,
        "vendor_id": machine.get("vendor_id"),
        "user_id": user["user_id"],
        "user_name": user.get("name", user.get("email", "Unknown")),
        "details": {
            "machine_name": machine.get("name", "") or f"{machine.get('brand', '')} {machine.get('model', '')}".strip(),
            "machine_category": machine.get("machine_category", ""),
            "machine_type": machine.get("machine_type", ""),
            "vendor_name": vendor.get("company_name", "Unknown") if vendor else "Unknown"
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activity_logs.insert_one(activity_log)
    
    logger.info(f"Machine deleted: {machine_id} by user {user['user_id']}")
    
    return {"message": "Machine deleted successfully"}


@api_router.post("/admin/machines/{machine_id}/images")
async def admin_upload_machine_image(
    machine_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload an image for any machine (admin or users with machines.manage_images permission)"""
    from app.services.s3_storage_service import upload_file
    
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.manage_images")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'machines.manage_images' permission.")
    
    # Get machine
    machine = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Check max images limit (5)
    current_images = machine.get("images", [])
    if len(current_images) >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed per machine")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")
    
    # Read file content
    content = await file.read()
    
    # Check file size (max 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be less than 5MB")
    
    # Upload to AWS S3
    try:
        result = upload_file(
            data=content,
            filename=file.filename,
            folder=f"machines/{machine['vendor_id']}",
            content_type=file.content_type
        )
        image_url = result["url"]  # Use presigned URL
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image to storage: {str(e)}")
    
    # Update machine with new image
    current_images = machine.get("images", [])
    current_images.append(image_url)
    
    await db.machines.update_one(
        {"machine_id": machine_id},
        {"$set": {"images": current_images}}
    )
    
    logger.info(f"Admin uploaded machine image to S3: {machine_id} - {image_url}")
    
    return {"image_url": image_url, "images": current_images}


@api_router.delete("/admin/machines/{machine_id}/images")
async def admin_delete_machine_image(
    machine_id: str,
    image_url: str,
    user: dict = Depends(get_current_user)
):
    """Delete an image from any machine (admin or users with machines.manage_images permission)"""
    from app.services.s3_storage_service import delete_file as s3_delete_file
    
    # Check for admin access OR specific permission
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.manage_images")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied. Requires 'machines.manage_images' permission.")
    
    # Get machine
    machine = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    current_images = machine.get("images", [])
    if image_url not in current_images:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Remove from list
    current_images.remove(image_url)
    
    await db.machines.update_one(
        {"machine_id": machine_id},
        {"$set": {"images": current_images}}
    )
    
    # Delete file from S3 if it's an S3 URL
    bucket_name = os.environ.get("AWS_S3_BUCKET_NAME", "oemlinker-storage")
    if f"{bucket_name}" in image_url or "s3." in image_url:
        # Extract S3 key from URL
        try:
            if ".amazonaws.com/" in image_url:
                s3_key = image_url.split(".amazonaws.com/")[1].split("?")[0]
                # Handle regional endpoint format: s3.region.amazonaws.com/bucket/key
                if s3_key.startswith(f"{bucket_name}/"):
                    s3_key = s3_key[len(bucket_name)+1:]
                s3_delete_file(s3_key)
                logger.info(f"Admin deleted S3 file: {s3_key}")
        except Exception as e:
            logger.warning(f"Failed to delete S3 file {image_url}: {e}")
    
    return {"message": "Image deleted", "images": current_images}


# ============== ACTIVITY LOGS ==============

@api_router.get("/admin/activity-logs")
async def get_activity_logs(
    user: dict = Depends(get_current_user),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    vendor_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get activity logs (admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    if vendor_id:
        query["vendor_id"] = vendor_id
    
    logs = await db.activity_logs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.activity_logs.count_documents(query)
    
    return {"logs": logs, "total": total, "limit": limit, "skip": skip}


@api_router.get("/admin/activity-logs/machines")
async def get_machine_activity_logs(
    user: dict = Depends(get_current_user),
    vendor_id: Optional[str] = None,
    limit: int = 50
):
    """Get machine-related activity logs"""
    if not has_admin_access(user):
        from app.services.rbac_service import rbac_service
        has_permission = await rbac_service.check_permission(user["user_id"], "machines.view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    query = {"entity_type": "machine"}
    if vendor_id:
        query["vendor_id"] = vendor_id
    
    logs = await db.activity_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs


# ============== DASHBOARD STATS ==============

@api_router.get("/buyer/quotes")
async def get_buyer_quotes(user: dict = Depends(get_current_user)):
    """Get all quotes received by the buyer across all their RFQs"""
    if user["role"] != UserRole.BUYER:
        raise HTTPException(status_code=403, detail="Buyer access required")
    
    # Get all RFQs for this buyer
    rfqs = await db.rfqs.find({"buyer_id": user["user_id"]}, {"_id": 0}).to_list(500)
    rfq_map = {rfq["rfq_id"]: rfq for rfq in rfqs}
    rfq_ids = list(rfq_map.keys())
    
    if not rfq_ids:
        return []
    
    # Get all quotes for buyer's RFQs
    quotes = await db.quotes.find(
        {"rfq_id": {"$in": rfq_ids}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    # Enrich quotes with vendor and RFQ info
    enriched_quotes = []
    for quote in quotes:
        # Get vendor info
        vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0})
        if vendor:
            quote["vendor_name"] = vendor.get("company_name", "Unknown")
            quote["vendor_rating"] = vendor.get("rating", 0)
            quote["vendor_location"] = f"{vendor.get('city', '')}, {vendor.get('country', '')}".strip(", ")
            quote["vendor_user_id"] = vendor.get("user_id")
            
            # Calculate acceptance rate
            total_quotes = await db.quotes.count_documents({"vendor_id": vendor["vendor_id"]})
            accepted_quotes = await db.quotes.count_documents({"vendor_id": vendor["vendor_id"], "status": "accepted"})
            quote["vendor_acceptance_rate"] = round((accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0, 1)
        
        # Add RFQ info
        rfq = rfq_map.get(quote["rfq_id"], {})
        quote["rfq_title"] = rfq.get("title", "Untitled RFQ")
        quote["rfq_material_type"] = rfq.get("material_type")
        quote["rfq_quantity"] = rfq.get("quantity")
        quote["rfq_tolerance"] = rfq.get("tolerance")
        quote["rfq_supply_type"] = rfq.get("supply_type", "vendor_material")
        quote["rfq_preferred_payment_terms"] = rfq.get("preferred_payment_terms")
        quote["rfq_status"] = rfq.get("status")
        
        # Get latest negotiation for this quote
        latest_negotiation = await db.quote_negotiations.find_one(
            {"quote_id": quote["quote_id"]},
            {"_id": 0}
        )
        if latest_negotiation:
            quote["latest_negotiation"] = latest_negotiation
        
        enriched_quotes.append(quote)
    
    return enriched_quotes

@api_router.get("/dashboard/buyer")
async def get_buyer_dashboard(user: dict = Depends(get_current_user)):
    rfqs = await db.rfqs.find({"buyer_id": user["user_id"]}, {"_id": 0}).to_list(100)
    orders = await db.orders.find({"buyer_id": user["user_id"]}, {"_id": 0}).to_list(100)
    
    # Count quotes received
    quotes_received = 0
    for rfq in rfqs:
        rfq_quotes = await db.quotes.count_documents({"rfq_id": rfq["rfq_id"]})
        quotes_received += rfq_quotes
    
    return {
        "total_rfqs": len(rfqs),
        "active_rfqs": len([r for r in rfqs if r["status"] not in [RFQStatus.COMPLETED, RFQStatus.CANCELLED]]),
        "pending_quotes": quotes_received,
        "total_orders": len(orders),
        "active_orders": len([o for o in orders if o["status"] not in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]]),
        "recent_rfqs": rfqs[:5],
        "recent_orders": orders[:5]
    }

@api_router.get("/vendor/matched-rfqs")
async def get_vendor_matched_rfqs(user: dict = Depends(get_current_user)):
    """Get all RFQs matched to this vendor with quote status"""
    if user["role"] != UserRole.VENDOR:
        raise HTTPException(status_code=403, detail="Vendor access required")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    vendor_id = vendor["vendor_id"]
    
    # Get all RFQs where this vendor is in matched_vendors
    matched_rfqs = await db.rfqs.find(
        {"matched_vendors.vendor_id": vendor_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    # Get all quotes by this vendor
    quotes = await db.quotes.find({"vendor_id": vendor_id}, {"_id": 0}).to_list(500)
    quotes_by_rfq = {q["rfq_id"]: q for q in quotes}
    
    # Enrich RFQs with vendor's quote info and match score
    enriched_rfqs = []
    for rfq in matched_rfqs:
        # Get buyer info
        buyer = await db.users.find_one({"user_id": rfq.get("buyer_id")}, {"_id": 0, "name": 1, "company_name": 1})
        
        # Find this vendor's match info
        match_info = next((v for v in rfq.get("matched_vendors", []) if v.get("vendor_id") == vendor_id), {})
        
        enriched_rfq = {
            "rfq_id": rfq["rfq_id"],
            "title": rfq.get("title", "Untitled"),
            "description": rfq.get("description", ""),
            "material_type": rfq.get("material_type", ""),
            "quantity": rfq.get("quantity", 1),
            "tolerance": rfq.get("tolerance", 0),
            "surface_finish": rfq.get("surface_finish", ""),
            "status": rfq.get("status", ""),
            "created_at": rfq.get("created_at", ""),
            "deadline": rfq.get("deadline"),
            "preferred_payment_terms": rfq.get("preferred_payment_terms"),
            "buyer_id": rfq.get("buyer_id"),
            "buyer_company": buyer.get("company_name") or buyer.get("name", "Unknown") if buyer else "Unknown",
            "match_score": match_info.get("suitability_score", 0),
            "matching_machines": match_info.get("matching_machines", []),
            "vendor_quote": quotes_by_rfq.get(rfq["rfq_id"])
        }
        enriched_rfqs.append(enriched_rfq)
    
    return {
        "rfqs": enriched_rfqs,
        "total": len(enriched_rfqs),
        "quoted": len([r for r in enriched_rfqs if r.get("vendor_quote")]),
        "pending": len([r for r in enriched_rfqs if not r.get("vendor_quote")])
    }

@api_router.get("/dashboard/vendor")
async def get_vendor_dashboard(user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        return {"error": "Vendor profile not found"}
    
    machines = await db.machines.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).to_list(50)
    quotes = await db.quotes.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).to_list(100)
    orders = await db.orders.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).to_list(100)
    
    # Get matched RFQs
    matched_rfqs = await db.rfqs.find(
        {"matched_vendors.vendor_id": vendor["vendor_id"]},
        {"_id": 0}
    ).to_list(50)
    
    total_revenue = sum(o.get("total_amount", 0) for o in orders if o.get("payment_status") == "paid")
    
    return {
        "vendor_profile": vendor,
        "total_machines": len(machines),
        "matched_rfqs": len(matched_rfqs),
        "quotes_submitted": len(quotes),
        "quotes_accepted": len([q for q in quotes if q.get("status") == "accepted"]),
        "total_orders": len(orders),
        "active_orders": len([o for o in orders if o["status"] not in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]]),
        "total_revenue": total_revenue,
        "recent_rfqs": matched_rfqs[:5],
        "recent_orders": orders[:5]
    }

# ============== PLATFORM ANALYTICS (ADMIN) ==============

@api_router.get("/admin/analytics")
async def get_platform_analytics(user: dict = Depends(get_current_user)):
    """Get comprehensive platform analytics for admin dashboard"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # ============== USER METRICS ==============
    total_users = await db.users.count_documents({})
    total_buyers = await db.users.count_documents({"role": "buyer"})
    total_vendors = await db.users.count_documents({"role": "vendor"})
    
    # New users this week/month
    new_users_week = await db.users.count_documents({
        "created_at": {"$gte": week_ago.isoformat()}
    })
    new_users_month = await db.users.count_documents({
        "created_at": {"$gte": month_ago.isoformat()}
    })
    new_users_today = await db.users.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    # Verified users
    verified_users = await db.users.count_documents({"email_verified": True})
    
    # ============== VENDOR METRICS ==============
    total_vendor_profiles = await db.vendors.count_documents({})
    approved_vendors = await db.vendors.count_documents({"is_approved": True})
    pending_vendors = await db.vendors.count_documents({"is_approved": False})
    
    # Top vendors by jobs
    top_vendors = await db.vendors.find(
        {"is_approved": True},
        {"_id": 0, "company_name": 1, "total_jobs": 1, "rating": 1, "city": 1}
    ).sort("total_jobs", -1).to_list(10)
    
    # ============== MACHINE METRICS ==============
    total_machines = await db.machines.count_documents({})
    active_machines = await db.machines.count_documents({"is_active": True})
    available_machines = await db.machines.count_documents({"availability_status": "available"})
    engaged_machines = await db.machines.count_documents({"availability_status": "engaged"})
    
    # Machines by category
    machine_categories = await db.machines.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$machine_category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    # ============== RFQ METRICS ==============
    total_rfqs = await db.rfqs.count_documents({})
    
    # RFQs by status
    rfq_statuses = await db.rfqs.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)
    rfq_by_status = {s["_id"]: s["count"] for s in rfq_statuses}
    
    # RFQs by urgency
    rfq_urgencies = await db.rfqs.aggregate([
        {"$group": {"_id": "$urgency", "count": {"$sum": 1}}}
    ]).to_list(10)
    rfq_by_urgency = {u["_id"] or "normal": u["count"] for u in rfq_urgencies}
    
    # New RFQs this week/month
    new_rfqs_week = await db.rfqs.count_documents({
        "created_at": {"$gte": week_ago.isoformat()}
    })
    new_rfqs_month = await db.rfqs.count_documents({
        "created_at": {"$gte": month_ago.isoformat()}
    })
    new_rfqs_today = await db.rfqs.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    # RFQs with matches
    rfqs_with_matches = await db.rfqs.count_documents({
        "matched_vendors": {"$exists": True, "$ne": []}
    })
    
    # ============== QUOTE METRICS ==============
    total_quotes = await db.quotes.count_documents({})
    accepted_quotes = await db.quotes.count_documents({"status": "accepted"})
    pending_quotes = await db.quotes.count_documents({"status": "pending"})
    rejected_quotes = await db.quotes.count_documents({"status": "rejected"})
    
    # Quote values
    all_quotes = await db.quotes.find({}, {"_id": 0, "price": 1, "status": 1}).to_list(10000)
    total_quote_value = sum(q.get("price", 0) for q in all_quotes)
    accepted_quote_value = sum(q.get("price", 0) for q in all_quotes if q.get("status") == "accepted")
    avg_quote_value = total_quote_value / len(all_quotes) if all_quotes else 0
    
    # Quote conversion rate
    quote_conversion_rate = (accepted_quotes / total_quotes * 100) if total_quotes > 0 else 0
    
    # ============== ORDER METRICS ==============
    total_orders = await db.orders.count_documents({})
    
    # Orders by status
    order_statuses = await db.orders.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)
    orders_by_status = {s["_id"]: s["count"] for s in order_statuses}
    
    # Revenue metrics
    all_orders = await db.orders.find({}, {"_id": 0, "total_amount": 1, "payment_status": 1, "status": 1, "created_at": 1}).to_list(10000)
    total_revenue = sum(o.get("total_amount", 0) for o in all_orders)
    paid_revenue = sum(o.get("total_amount", 0) for o in all_orders if o.get("payment_status") == "paid")
    pending_revenue = sum(o.get("total_amount", 0) for o in all_orders if o.get("payment_status") == "pending")
    
    completed_orders = await db.orders.count_documents({"status": "completed"})
    active_orders = await db.orders.count_documents({
        "status": {"$nin": ["completed", "cancelled"]}
    })
    
    # Monthly revenue trend (last 6 months)
    monthly_revenue = []
    for i in range(6):
        month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        month_orders = [o for o in all_orders 
                       if o.get("created_at") and month_start.isoformat() <= o["created_at"] < month_end.isoformat()]
        month_total = sum(o.get("total_amount", 0) for o in month_orders)
        monthly_revenue.append({
            "month": month_start.strftime("%b %Y"),
            "revenue": month_total,
            "orders": len(month_orders)
        })
    monthly_revenue.reverse()
    
    # ============== RECENT ACTIVITY ==============
    recent_users = await db.users.find(
        {}, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(5)
    
    recent_rfqs = await db.rfqs.find(
        {}, {"_id": 0, "rfq_id": 1, "title": 1, "status": 1, "urgency": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(5)
    
    recent_quotes = await db.quotes.find(
        {}, {"_id": 0, "quote_id": 1, "rfq_id": 1, "price": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(5)
    
    recent_orders = await db.orders.find(
        {}, {"_id": 0, "order_id": 1, "total_amount": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(5)
    
    # ============== PLATFORM HEALTH ==============
    # Calculate key rates
    rfq_match_rate = (rfqs_with_matches / total_rfqs * 100) if total_rfqs > 0 else 0
    vendor_approval_rate = (approved_vendors / total_vendor_profiles * 100) if total_vendor_profiles > 0 else 0
    machine_availability_rate = (available_machines / active_machines * 100) if active_machines > 0 else 0
    
    return {
        "generated_at": now.isoformat(),
        "summary": {
            "total_users": total_users,
            "total_rfqs": total_rfqs,
            "total_quotes": total_quotes,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "platform_gmv": total_quote_value
        },
        "users": {
            "total": total_users,
            "buyers": total_buyers,
            "vendors": total_vendors,
            "verified": verified_users,
            "verification_rate": round(verified_users / total_users * 100, 1) if total_users > 0 else 0,
            "new_today": new_users_today,
            "new_this_week": new_users_week,
            "new_this_month": new_users_month
        },
        "vendors": {
            "total_profiles": total_vendor_profiles,
            "approved": approved_vendors,
            "pending_approval": pending_vendors,
            "approval_rate": round(vendor_approval_rate, 1),
            "top_vendors": top_vendors
        },
        "machines": {
            "total": total_machines,
            "active": active_machines,
            "available": available_machines,
            "engaged": engaged_machines,
            "availability_rate": round(machine_availability_rate, 1),
            "by_category": machine_categories
        },
        "rfqs": {
            "total": total_rfqs,
            "by_status": rfq_by_status,
            "by_urgency": rfq_by_urgency,
            "with_matches": rfqs_with_matches,
            "match_rate": round(rfq_match_rate, 1),
            "new_today": new_rfqs_today,
            "new_this_week": new_rfqs_week,
            "new_this_month": new_rfqs_month
        },
        "quotes": {
            "total": total_quotes,
            "accepted": accepted_quotes,
            "pending": pending_quotes,
            "rejected": rejected_quotes,
            "conversion_rate": round(quote_conversion_rate, 1),
            "total_value": total_quote_value,
            "accepted_value": accepted_quote_value,
            "average_value": round(avg_quote_value, 2)
        },
        "orders": {
            "total": total_orders,
            "completed": completed_orders,
            "active": active_orders,
            "by_status": orders_by_status
        },
        "revenue": {
            "total": total_revenue,
            "paid": paid_revenue,
            "pending": pending_revenue,
            "monthly_trend": monthly_revenue
        },
        "recent_activity": {
            "users": recent_users,
            "rfqs": recent_rfqs,
            "quotes": recent_quotes,
            "orders": recent_orders
        },
        "health": {
            "rfq_match_rate": round(rfq_match_rate, 1),
            "quote_conversion_rate": round(quote_conversion_rate, 1),
            "vendor_approval_rate": round(vendor_approval_rate, 1),
            "machine_availability_rate": round(machine_availability_rate, 1)
        }
    }

@api_router.get("/admin/analytics/export")
async def export_analytics_csv(user: dict = Depends(get_current_user)):
    """Export analytics data as CSV"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    import csv
    from io import StringIO
    
    # Get all orders for export
    orders = await db.orders.find({}, {"_id": 0}).to_list(10000)
    
    output = StringIO()
    if orders:
        writer = csv.DictWriter(output, fieldnames=orders[0].keys())
        writer.writeheader()
        writer.writerows(orders)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders_export.csv"}
    )

# ============== WHATSAPP ADMIN - MESSAGE MANAGEMENT ==============

class WhatsAppMessageCreate(BaseModel):
    """Model for sending WhatsApp messages"""
    phone: str
    message: str
    template_name: Optional[str] = None
    template_params: Optional[List[str]] = None

class WhatsAppBroadcast(BaseModel):
    """Model for broadcast messages"""
    phone_numbers: List[str]
    message: str
    template_name: Optional[str] = None
    template_params: Optional[List[str]] = None

# Store for WhatsApp messages
async def store_whatsapp_message(
    phone: str,
    direction: str,  # "incoming" or "outgoing"
    message_type: str,  # "text", "image", "audio", "video", "document", "template"
    content: str,
    vendor_id: Optional[str] = None,
    vendor_name: Optional[str] = None,
    message_id: Optional[str] = None,
    template_name: Optional[str] = None,
    sent_by: Optional[str] = None,  # user_id of sender for outgoing
    media_url: Optional[str] = None,  # URL for images, videos, documents
    media_type: Optional[str] = None,  # mime type of media
    thumbnail_url: Optional[str] = None,  # thumbnail for videos
    filename: Optional[str] = None  # original filename for documents
):
    """Store a WhatsApp message in the database"""
    msg_doc = {
        "message_id": message_id or f"msg_{uuid.uuid4().hex[:12]}",
        "phone": phone,
        "phone_normalized": phone.replace("+", "").replace(" ", "").replace("-", "")[-10:],
        "direction": direction,
        "message_type": message_type,
        "content": content[:2000] if content else "",  # Limit content length
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "template_name": template_name,
        "sent_by": sent_by,
        "read": direction == "outgoing",  # Outgoing messages are auto-read
        "media_url": media_url,
        "media_type": media_type,
        "thumbnail_url": thumbnail_url,
        "filename": filename,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.whatsapp_messages.insert_one(msg_doc)
    return msg_doc["message_id"]

@api_router.get("/admin/whatsapp/conversations")
async def admin_get_whatsapp_conversations(
    user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None
):
    """Get list of WhatsApp conversations grouped by phone number"""
    if user["role"] != UserRole.ADMIN and not user.get("whatsapp_admin"):
        raise HTTPException(status_code=403, detail="WhatsApp admin access required")
    
    # Build aggregation pipeline
    pipeline = [
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$phone_normalized",
            "phone": {"$first": "$phone"},
            "vendor_id": {"$first": "$vendor_id"},
            "vendor_name": {"$first": "$vendor_name"},
            "last_message": {"$first": "$content"},
            "last_message_time": {"$first": "$created_at"},
            "last_direction": {"$first": "$direction"},
            "message_count": {"$sum": 1},
            "unread_count": {"$sum": {"$cond": [{"$and": [{"$eq": ["$direction", "incoming"]}, {"$eq": ["$read", False]}]}, 1, 0]}}
        }},
        {"$sort": {"last_message_time": -1}}
    ]
    
    # Add search filter if provided
    if search:
        pipeline.insert(0, {
            "$match": {
                "$or": [
                    {"phone": {"$regex": search, "$options": "i"}},
                    {"vendor_name": {"$regex": search, "$options": "i"}},
                    {"content": {"$regex": search, "$options": "i"}}
                ]
            }
        })
    
    # Add pagination
    pipeline.extend([
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ])
    
    conversations = await db.whatsapp_messages.aggregate(pipeline).to_list(limit)
    
    # Get total count
    count_pipeline = [
        {"$group": {"_id": "$phone_normalized"}},
        {"$count": "total"}
    ]
    count_result = await db.whatsapp_messages.aggregate(count_pipeline).to_list(1)
    total = count_result[0]["total"] if count_result else 0
    
    return {
        "conversations": conversations,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@api_router.get("/admin/whatsapp/conversations/{phone}")
async def admin_get_conversation_messages(
    phone: str,
    user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 100
):
    """Get messages for a specific phone number"""
    if user["role"] != UserRole.ADMIN and not user.get("whatsapp_admin"):
        raise HTTPException(status_code=403, detail="WhatsApp admin access required")
    
    # Normalize phone number
    phone_normalized = phone.replace("+", "").replace(" ", "").replace("-", "")[-10:]
    
    # Get messages
    messages = await db.whatsapp_messages.find(
        {"phone_normalized": phone_normalized},
        {"_id": 0}
    ).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    
    # Reverse to show oldest first in conversation view
    messages.reverse()
    
    # Mark incoming messages as read
    await db.whatsapp_messages.update_many(
        {"phone_normalized": phone_normalized, "direction": "incoming", "read": False},
        {"$set": {"read": True}}
    )
    
    # Get vendor info
    vendor = await db.vendors.find_one(
        {"phone": {"$regex": phone_normalized}},
        {"_id": 0, "vendor_id": 1, "company_name": 1, "city": 1, "state": 1}
    )
    
    # Get total message count
    total = await db.whatsapp_messages.count_documents({"phone_normalized": phone_normalized})
    
    return {
        "messages": messages,
        "vendor": vendor,
        "phone": phone,
        "total": total,
        "page": page,
        "limit": limit
    }

@api_router.post("/admin/whatsapp/send")
async def admin_send_whatsapp_message(
    msg: WhatsAppMessageCreate,
    user: dict = Depends(get_current_user)
):
    """Send a WhatsApp message to a phone number"""
    if user["role"] != UserRole.ADMIN and not user.get("whatsapp_admin"):
        raise HTTPException(status_code=403, detail="WhatsApp admin access required")
    
    if not whatsapp_service.is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp service not configured")
    
    # Normalize phone number
    phone = msg.phone.replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        if phone.startswith("91"):
            phone = f"+{phone}"
        else:
            phone = f"+91{phone}"
    
    # Get vendor info for storing
    phone_normalized = phone.replace("+", "")[-10:]
    vendor = await db.vendors.find_one(
        {"phone": {"$regex": phone_normalized}},
        {"_id": 0, "vendor_id": 1, "company_name": 1}
    )
    
    # Template definitions with actual content
    TEMPLATE_CONTENTS = {
        "machine_upload_reminder": """Hello Team {0},
📷Send photos of your machines to receive RFQs based on the machines you have.
Or
✏️ Edit details at https://oemlinker.com/vendor/machines
Thanks Team OEMLinker""",
        "rfq_notification": """Hello {0},
🔔 New RFQ matching your capabilities is available!
Check OEMLinker to view details and submit your quote.
Team OEMLinker""",
        "quote_reminder": """Hello {0},
⏰ Reminder: You have pending RFQs waiting for your quote.
Submit your quotes at https://oemlinker.com
Team OEMLinker"""
    }
    
    # Send message
    if msg.template_name and msg.template_name in TEMPLATE_CONTENTS:
        # Format template with parameters
        template_content = TEMPLATE_CONTENTS[msg.template_name]
        params = msg.template_params or []
        try:
            formatted_message = template_content.format(*params)
        except (IndexError, KeyError):
            formatted_message = template_content
        
        # Send as regular text message (formatted template)
        result = await whatsapp_service.send_text_message(phone, formatted_message)
        message_type = "template"
        content = formatted_message
    elif msg.template_name:
        # Unknown template - send the message as-is
        result = await whatsapp_service.send_text_message(phone, msg.message)
        message_type = "template"
        content = msg.message
    else:
        # Send regular text message
        result = await whatsapp_service.send_text_message(phone, msg.message)
        message_type = "text"
        content = msg.message
    
    # Store the outgoing message
    await store_whatsapp_message(
        phone=phone,
        direction="outgoing",
        message_type=message_type,
        content=content,
        vendor_id=vendor.get("vendor_id") if vendor else None,
        vendor_name=vendor.get("company_name") if vendor else None,
        template_name=msg.template_name,
        sent_by=user["user_id"]
    )
    
    return {
        "success": result,
        "phone": phone,
        "message": "Message sent successfully" if result else "Failed to send message"
    }

@api_router.post("/admin/whatsapp/broadcast")
async def admin_broadcast_whatsapp(
    broadcast: WhatsAppBroadcast,
    user: dict = Depends(get_current_user)
):
    """Send a broadcast message to multiple phone numbers"""
    if user["role"] != UserRole.ADMIN and not user.get("whatsapp_admin"):
        raise HTTPException(status_code=403, detail="WhatsApp admin access required")
    
    if not whatsapp_service.is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp service not configured")
    
    # Template definitions
    TEMPLATE_CONTENTS = {
        "machine_upload_reminder": """Hello Team {0},
📷Send photos of your machines to receive RFQs based on the machines you have.
Or
✏️ Edit details at https://oemlinker.com/vendor/machines
Thanks Team OEMLinker""",
        "rfq_notification": """Hello {0},
🔔 New RFQ matching your capabilities is available!
Check OEMLinker to view details and submit your quote.
Team OEMLinker""",
        "quote_reminder": """Hello {0},
⏰ Reminder: You have pending RFQs waiting for your quote.
Submit your quotes at https://oemlinker.com
Team OEMLinker"""
    }
    
    results = {
        "success": [],
        "failed": []
    }
    
    for phone in broadcast.phone_numbers:
        try:
            # Normalize phone
            phone_clean = phone.replace(" ", "").replace("-", "")
            if not phone_clean.startswith("+"):
                if phone_clean.startswith("91"):
                    phone_clean = f"+{phone_clean}"
                else:
                    phone_clean = f"+91{phone_clean}"
            
            # Get vendor info
            phone_normalized = phone_clean.replace("+", "")[-10:]
            vendor = await db.vendors.find_one(
                {"phone": {"$regex": phone_normalized}},
                {"_id": 0, "vendor_id": 1, "company_name": 1}
            )
            
            # Send message
            if broadcast.template_name and broadcast.template_name in TEMPLATE_CONTENTS:
                # Format template with parameters
                template_content = TEMPLATE_CONTENTS[broadcast.template_name]
                params = broadcast.template_params or []
                try:
                    formatted_message = template_content.format(*params)
                except (IndexError, KeyError):
                    formatted_message = template_content
                
                result = await whatsapp_service.send_text_message(phone_clean, formatted_message)
                message_type = "template"
                content = formatted_message
            elif broadcast.template_name:
                result = await whatsapp_service.send_text_message(phone_clean, broadcast.message)
                message_type = "template"
                content = broadcast.message
            else:
                result = await whatsapp_service.send_text_message(phone_clean, broadcast.message)
                message_type = "text"
                content = broadcast.message
            
            if result and result.get("success"):
                results["success"].append(phone)
                # Store outgoing message
                await store_whatsapp_message(
                    phone=phone_clean,
                    direction="outgoing",
                    message_type=message_type,
                    content=content,
                    vendor_id=vendor.get("vendor_id") if vendor else None,
                    vendor_name=vendor.get("company_name") if vendor else None,
                    template_name=broadcast.template_name,
                    sent_by=user["user_id"]
                )
            else:
                results["failed"].append(phone)
                
        except Exception as e:
            logger.error(f"Failed to send to {phone}: {str(e)}")
            results["failed"].append(phone)
    
    return {
        "total": len(broadcast.phone_numbers),
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "results": results
    }

@api_router.get("/admin/whatsapp/stats")
async def admin_get_whatsapp_stats(user: dict = Depends(get_current_user)):
    """Get WhatsApp messaging statistics"""
    if user["role"] != UserRole.ADMIN and not user.get("whatsapp_admin"):
        raise HTTPException(status_code=403, detail="WhatsApp admin access required")
    
    # Get counts
    total_messages = await db.whatsapp_messages.count_documents({})
    incoming = await db.whatsapp_messages.count_documents({"direction": "incoming"})
    outgoing = await db.whatsapp_messages.count_documents({"direction": "outgoing"})
    unread = await db.whatsapp_messages.count_documents({"direction": "incoming", "read": False})
    
    # Get unique conversations
    unique_phones = await db.whatsapp_messages.distinct("phone_normalized")
    
    # Get messages today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_messages = await db.whatsapp_messages.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    return {
        "total_messages": total_messages,
        "incoming": incoming,
        "outgoing": outgoing,
        "unread": unread,
        "unique_conversations": len(unique_phones),
        "messages_today": today_messages
    }

@api_router.post("/admin/whatsapp/grant-access/{user_id}")
async def admin_grant_whatsapp_access(user_id: str, user: dict = Depends(get_current_user)):
    """Grant WhatsApp admin access to a user"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"whatsapp_admin": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "WhatsApp admin access granted"}

@api_router.post("/admin/whatsapp/revoke-access/{user_id}")
async def admin_revoke_whatsapp_access(user_id: str, user: dict = Depends(get_current_user)):
    """Revoke WhatsApp admin access from a user"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"whatsapp_admin": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "WhatsApp admin access revoked"}

@api_router.get("/admin/whatsapp/users-with-access")
async def admin_get_whatsapp_users(user: dict = Depends(get_current_user)):
    """Get list of users with WhatsApp admin access"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find(
        {"whatsapp_admin": True},
        {"_id": 0, "user_id": 1, "email": 1, "name": 1, "role": 1}
    ).to_list(100)
    
    return users

# ============== META/WHATSAPP DATA DELETION COMPLIANCE ==============

class DataDeletionRequest(BaseModel):
    """Model for user data deletion request"""
    phone: Optional[str] = None
    email: Optional[str] = None
    reason: Optional[str] = None

class DataDeletionCallback(BaseModel):
    """Model for Meta's data deletion callback"""
    signed_request: str

import hmac
import hashlib
import base64

def parse_signed_request(signed_request: str, app_secret: str) -> Optional[dict]:
    """Parse and verify Meta's signed request"""
    try:
        encoded_sig, payload = signed_request.split('.', 1)
        
        # Decode signature
        sig = base64.urlsafe_b64decode(encoded_sig + '==')
        
        # Decode payload
        data = base64.urlsafe_b64decode(payload + '==')
        data = json.loads(data)
        
        # Verify signature
        expected_sig = hmac.new(
            app_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        if hmac.compare_digest(sig, expected_sig):
            return data
        return None
    except Exception as e:
        logger.error(f"Error parsing signed request: {e}")
        return None

@api_router.post("/meta/data-deletion-callback")
async def meta_data_deletion_callback(request: Request):
    """
    Meta/WhatsApp Data Deletion Callback URL
    This endpoint is called by Meta when a user requests data deletion from Facebook/WhatsApp
    
    Required for WhatsApp Business API compliance
    """
    try:
        form_data = await request.form()
        signed_request = form_data.get("signed_request", "")
        
        # Get app secret from environment (you need to set this)
        app_secret = os.environ.get("META_APP_SECRET", "")
        
        if not app_secret:
            logger.warning("META_APP_SECRET not configured")
            # Still process the request but log warning
        
        # Parse the signed request
        user_data = None
        if app_secret and signed_request:
            user_data = parse_signed_request(signed_request, app_secret)
        
        user_id = user_data.get("user_id") if user_data else None
        
        # Generate a confirmation code
        confirmation_code = f"DEL_{uuid.uuid4().hex[:12].upper()}"
        
        # Store the deletion request
        deletion_record = {
            "confirmation_code": confirmation_code,
            "meta_user_id": user_id,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "source": "meta_callback"
        }
        await db.data_deletion_requests.insert_one(deletion_record)
        
        # Log the deletion request
        logger.info(f"Meta data deletion callback received. Confirmation: {confirmation_code}")
        
        # Return the required response format
        # Meta expects a URL where the user can check the status and a confirmation code
        base_url = os.environ.get("FRONTEND_URL", "https://oemlinker.com")
        status_url = f"{base_url}/data-deletion-status?code={confirmation_code}"
        
        return {
            "url": status_url,
            "confirmation_code": confirmation_code
        }
        
    except Exception as e:
        logger.error(f"Error processing Meta data deletion callback: {e}")
        raise HTTPException(status_code=500, detail="Error processing deletion request")

@api_router.get("/data-deletion/status/{confirmation_code}")
async def get_data_deletion_status(confirmation_code: str):
    """Get the status of a data deletion request"""
    record = await db.data_deletion_requests.find_one(
        {"confirmation_code": confirmation_code},
        {"_id": 0}
    )
    
    if not record:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    
    return {
        "confirmation_code": record.get("confirmation_code"),
        "status": record.get("status"),
        "requested_at": record.get("requested_at"),
        "completed_at": record.get("completed_at"),
        "message": get_deletion_status_message(record.get("status"))
    }

def get_deletion_status_message(status: str) -> str:
    """Get human-readable status message"""
    messages = {
        "pending": "Your data deletion request has been received and is being processed.",
        "in_progress": "Your data is currently being deleted from our systems.",
        "completed": "Your data has been successfully deleted from our systems.",
        "failed": "There was an error processing your request. Please contact support."
    }
    return messages.get(status, "Unknown status")

@api_router.post("/data-deletion/request")
async def request_data_deletion(request_data: DataDeletionRequest):
    """
    User-initiated data deletion request
    Users can request deletion of their data via phone number or email
    """
    if not request_data.phone and not request_data.email:
        raise HTTPException(status_code=400, detail="Please provide phone number or email")
    
    # Find the user
    user = None
    if request_data.email:
        user = await db.users.find_one({"email": request_data.email}, {"_id": 0})
    if not user and request_data.phone:
        phone_normalized = request_data.phone.replace("+", "").replace(" ", "").replace("-", "")[-10:]
        user = await db.users.find_one(
            {"$or": [
                {"email": phone_normalized},
                {"phone": {"$regex": phone_normalized}},
                {"contact_email": request_data.email} if request_data.email else {"_id": None}
            ]},
            {"_id": 0}
        )
    
    # Generate confirmation code
    confirmation_code = f"DEL_{uuid.uuid4().hex[:12].upper()}"
    
    # Store the deletion request
    deletion_record = {
        "confirmation_code": confirmation_code,
        "phone": request_data.phone,
        "email": request_data.email,
        "user_id": user.get("user_id") if user else None,
        "reason": request_data.reason,
        "status": "pending",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "source": "user_request"
    }
    await db.data_deletion_requests.insert_one(deletion_record)
    
    logger.info(f"User data deletion request received. Confirmation: {confirmation_code}")
    
    return {
        "success": True,
        "confirmation_code": confirmation_code,
        "message": "Your data deletion request has been received. You will receive confirmation once the deletion is complete.",
        "status_url": f"/data-deletion-status?code={confirmation_code}"
    }

@api_router.post("/admin/data-deletion/process/{confirmation_code}")
async def process_data_deletion(confirmation_code: str, user: dict = Depends(get_current_user)):
    """
    Admin endpoint to process a data deletion request
    This actually deletes the user's data from the database
    """
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Find the deletion request
    record = await db.data_deletion_requests.find_one({"confirmation_code": confirmation_code})
    if not record:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    
    if record.get("status") == "completed":
        return {"message": "This deletion request has already been processed"}
    
    # Update status to in_progress
    await db.data_deletion_requests.update_one(
        {"confirmation_code": confirmation_code},
        {"$set": {"status": "in_progress"}}
    )
    
    deleted_data = {
        "users": 0,
        "vendors": 0,
        "machines": 0,
        "whatsapp_messages": 0,
        "quotes": 0
    }
    
    try:
        user_id = record.get("user_id")
        phone = record.get("phone")
        email = record.get("email")
        
        if user_id:
            # Delete user data
            result = await db.users.delete_one({"user_id": user_id})
            deleted_data["users"] = result.deleted_count
            
            # Delete vendor profile
            vendor = await db.vendors.find_one({"user_id": user_id})
            if vendor:
                vendor_id = vendor.get("vendor_id")
                await db.vendors.delete_one({"vendor_id": vendor_id})
                deleted_data["vendors"] = 1
                
                # Delete machines
                result = await db.machines.delete_many({"vendor_id": vendor_id})
                deleted_data["machines"] = result.deleted_count
                
                # Delete quotes
                result = await db.quotes.delete_many({"vendor_id": vendor_id})
                deleted_data["quotes"] = result.deleted_count
        
        # Delete WhatsApp messages by phone
        if phone:
            phone_normalized = phone.replace("+", "").replace(" ", "").replace("-", "")[-10:]
            result = await db.whatsapp_messages.delete_many({"phone_normalized": phone_normalized})
            deleted_data["whatsapp_messages"] = result.deleted_count
        
        # Update deletion request status
        await db.data_deletion_requests.update_one(
            {"confirmation_code": confirmation_code},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "deleted_data": deleted_data,
                    "processed_by": user["user_id"]
                }
            }
        )
        
        logger.info(f"Data deletion completed for {confirmation_code}. Deleted: {deleted_data}")
        
        return {
            "success": True,
            "message": "Data deletion completed successfully",
            "deleted_data": deleted_data
        }
        
    except Exception as e:
        logger.error(f"Error processing data deletion: {e}")
        await db.data_deletion_requests.update_one(
            {"confirmation_code": confirmation_code},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Error processing deletion: {str(e)}")

@api_router.get("/admin/data-deletion/requests")
async def get_data_deletion_requests(
    user: dict = Depends(get_current_user),
    status: Optional[str] = None
):
    """Get all data deletion requests (admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    requests = await db.data_deletion_requests.find(query, {"_id": 0}).sort("requested_at", -1).to_list(100)
    return requests

# ============== DISPUTE RESOLUTION SYSTEM ==============

class DisputeType:
    QUALITY_ISSUE = "quality_issue"
    DELIVERY_DELAY = "delivery_delay"
    WRONG_SPECIFICATIONS = "wrong_specifications"
    PAYMENT_ISSUE = "payment_issue"
    COMMUNICATION = "communication"
    DAMAGED_GOODS = "damaged_goods"
    INCOMPLETE_ORDER = "incomplete_order"
    OTHER = "other"

class DisputeStatus:
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    AWAITING_RESPONSE = "awaiting_response"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ResolutionType:
    FULL_REFUND = "full_refund"
    PARTIAL_REFUND = "partial_refund"
    REPLACEMENT = "replacement"
    REWORK = "rework"
    NO_ACTION = "no_action"
    MUTUAL_AGREEMENT = "mutual_agreement"

class DisputeCreate(BaseModel):
    order_id: str
    dispute_type: str
    subject: str
    description: str
    expected_resolution: Optional[str] = None
    evidence_urls: List[str] = []

class DisputeResponse(BaseModel):
    message: str
    evidence_urls: List[str] = []

class DisputeResolve(BaseModel):
    resolution_type: str
    resolution_notes: str
    refund_amount: Optional[float] = None

@api_router.post("/disputes")
async def create_dispute(dispute_data: DisputeCreate, user: dict = Depends(get_current_user)):
    """Create a new dispute for an order"""
    # Verify order exists and user is involved
    order = await db.orders.find_one({"order_id": dispute_data.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if user is buyer or vendor of this order
    is_buyer = order.get("buyer_id") == user["user_id"]
    is_vendor = order.get("vendor_id") == user["user_id"]
    
    if not is_buyer and not is_vendor:
        raise HTTPException(status_code=403, detail="You are not authorized to create a dispute for this order")
    
    # Check if dispute already exists for this order
    existing_dispute = await db.disputes.find_one({
        "order_id": dispute_data.order_id,
        "status": {"$nin": [DisputeStatus.RESOLVED, DisputeStatus.CLOSED]}
    })
    if existing_dispute:
        raise HTTPException(status_code=400, detail="An active dispute already exists for this order")
    
    dispute_id = f"dispute_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Get order details for context
    rfq = await db.rfqs.find_one({"rfq_id": order.get("rfq_id")}, {"_id": 0, "title": 1})
    
    # Get user names
    buyer = await db.users.find_one({"user_id": order.get("buyer_id")}, {"_id": 0, "name": 1, "email": 1})
    vendor_profile = await db.vendors.find_one({"vendor_id": order.get("vendor_id")}, {"_id": 0, "company_name": 1})
    
    dispute_doc = {
        "dispute_id": dispute_id,
        "order_id": dispute_data.order_id,
        "rfq_id": order.get("rfq_id"),
        "rfq_title": rfq.get("title") if rfq else "N/A",
        "buyer_id": order.get("buyer_id"),
        "buyer_name": buyer.get("name") if buyer else "N/A",
        "buyer_email": buyer.get("email") if buyer else "N/A",
        "vendor_id": order.get("vendor_id"),
        "vendor_name": vendor_profile.get("company_name") if vendor_profile else "N/A",
        "initiated_by": "buyer" if is_buyer else "vendor",
        "initiator_id": user["user_id"],
        "initiator_name": user["name"],
        "dispute_type": dispute_data.dispute_type,
        "subject": dispute_data.subject,
        "description": dispute_data.description,
        "expected_resolution": dispute_data.expected_resolution,
        "order_amount": order.get("total_amount", 0),
        "status": DisputeStatus.OPEN,
        "priority": "normal",
        "resolution_type": None,
        "resolution_notes": None,
        "refund_amount": None,
        "resolved_by": None,
        "resolved_at": None,
        "timeline": [
            {
                "event": "dispute_created",
                "message": f"Dispute created by {user['name']}",
                "user_id": user["user_id"],
                "user_name": user["name"],
                "user_role": "buyer" if is_buyer else "vendor",
                "timestamp": now,
                "evidence_urls": dispute_data.evidence_urls
            }
        ],
        "created_at": now,
        "updated_at": now
    }
    
    await db.disputes.insert_one(dispute_doc)
    
    # Update order status
    await db.orders.update_one(
        {"order_id": dispute_data.order_id},
        {"$set": {"has_dispute": True, "dispute_id": dispute_id}}
    )
    
    # Notify the other party
    other_party_id = order.get("vendor_id") if is_buyer else order.get("buyer_id")
    notification_doc = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": other_party_id,
        "type": "dispute_created",
        "title": "New Dispute Filed",
        "message": f"A dispute has been filed for order #{dispute_data.order_id[:12]}",
        "data": {"dispute_id": dispute_id, "order_id": dispute_data.order_id},
        "is_read": False,
        "created_at": now
    }
    await db.notifications.insert_one(notification_doc)
    
    # Notify admin
    admin_notification = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": "admin",
        "type": "dispute_created",
        "title": "New Dispute Requires Attention",
        "message": f"Dispute #{dispute_id[:12]} filed for order #{dispute_data.order_id[:12]}",
        "data": {"dispute_id": dispute_id, "order_id": dispute_data.order_id},
        "is_read": False,
        "created_at": now
    }
    await db.notifications.insert_one(admin_notification)
    
    # Send email to admin
    asyncio.create_task(send_admin_notification("new_dispute", {
        "dispute_id": dispute_id,
        "order_id": dispute_data.order_id,
        "dispute_type": dispute_data.dispute_type.replace("_", " ").title(),
        "subject": dispute_data.subject,
        "initiated_by": user["name"],
        "buyer_name": buyer.get("name") if buyer else "N/A",
        "vendor_name": vendor_profile.get("company_name") if vendor_profile else "N/A",
        "order_amount": order.get("total_amount", 0),
        "created_at": now
    }))
    
    logger.info(f"Dispute created: {dispute_id} for order {dispute_data.order_id} by {user['email']}")
    
    dispute_doc.pop("_id", None)
    return {"message": "Dispute created successfully", "dispute": dispute_doc}

@api_router.get("/disputes")
async def get_disputes(
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get disputes for current user or all disputes for admin"""
    if user["role"] == UserRole.ADMIN:
        query = {}
    else:
        query = {"$or": [
            {"buyer_id": user["user_id"]},
            {"vendor_id": user["user_id"]}
        ]}
    
    if status:
        query["status"] = status
    
    disputes = await db.disputes.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    # Get counts by status
    status_counts = {}
    for s in [DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW, DisputeStatus.AWAITING_RESPONSE, 
              DisputeStatus.ESCALATED, DisputeStatus.RESOLVED, DisputeStatus.CLOSED]:
        count_query = {"status": s}
        if not has_admin_access(user):
            count_query["$or"] = [{"buyer_id": user["user_id"]}, {"vendor_id": user["user_id"]}]
        status_counts[s] = await db.disputes.count_documents(count_query)
    
    return {
        "disputes": disputes,
        "total": len(disputes),
        "status_counts": status_counts
    }

@api_router.get("/disputes/{dispute_id}")
async def get_dispute_detail(dispute_id: str, user: dict = Depends(get_current_user)):
    """Get detailed dispute information"""
    dispute = await db.disputes.find_one({"dispute_id": dispute_id}, {"_id": 0})
    
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    # Check authorization
    is_buyer = dispute.get("buyer_id") == user["user_id"]
    is_vendor = dispute.get("vendor_id") == user["user_id"]
    is_admin = user["role"] == UserRole.ADMIN
    
    if not (is_buyer or is_vendor or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view this dispute")
    
    # Get order details
    order = await db.orders.find_one({"order_id": dispute.get("order_id")}, {"_id": 0})
    
    return {
        "dispute": dispute,
        "order": order,
        "user_role": "admin" if is_admin else ("buyer" if is_buyer else "vendor")
    }

@api_router.post("/disputes/{dispute_id}/respond")
async def respond_to_dispute(
    dispute_id: str, 
    response_data: DisputeResponse, 
    user: dict = Depends(get_current_user)
):
    """Add a response/comment to a dispute"""
    dispute = await db.disputes.find_one({"dispute_id": dispute_id}, {"_id": 0})
    
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    # Check authorization
    is_buyer = dispute.get("buyer_id") == user["user_id"]
    is_vendor = dispute.get("vendor_id") == user["user_id"]
    is_admin = user["role"] == UserRole.ADMIN
    
    if not (is_buyer or is_vendor or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to respond to this dispute")
    
    if dispute["status"] in [DisputeStatus.RESOLVED, DisputeStatus.CLOSED]:
        raise HTTPException(status_code=400, detail="Cannot respond to a resolved or closed dispute")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Determine user role for timeline
    if is_admin:
        user_role = "admin"
    elif is_buyer:
        user_role = "buyer"
    else:
        user_role = "vendor"
    
    timeline_entry = {
        "event": "response_added",
        "message": response_data.message,
        "user_id": user["user_id"],
        "user_name": user["name"],
        "user_role": user_role,
        "timestamp": now,
        "evidence_urls": response_data.evidence_urls
    }
    
    # Update status based on who responded
    new_status = dispute["status"]
    if is_admin and dispute["status"] == DisputeStatus.OPEN:
        new_status = DisputeStatus.UNDER_REVIEW
    elif not is_admin and dispute["status"] == DisputeStatus.AWAITING_RESPONSE:
        new_status = DisputeStatus.UNDER_REVIEW
    
    await db.disputes.update_one(
        {"dispute_id": dispute_id},
        {
            "$push": {"timeline": timeline_entry},
            "$set": {"status": new_status, "updated_at": now}
        }
    )
    
    # Notify other parties
    notify_ids = []
    if is_buyer:
        notify_ids.append(dispute.get("vendor_id"))
    elif is_vendor:
        notify_ids.append(dispute.get("buyer_id"))
    else:  # admin
        notify_ids.extend([dispute.get("buyer_id"), dispute.get("vendor_id")])
    
    for notify_id in notify_ids:
        if notify_id:
            notification = {
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "user_id": notify_id,
                "type": "dispute_response",
                "title": "New Response in Dispute",
                "message": f"{user['name']} responded to dispute #{dispute_id[:12]}",
                "data": {"dispute_id": dispute_id},
                "is_read": False,
                "created_at": now
            }
            await db.notifications.insert_one(notification)
    
    logger.info(f"Response added to dispute {dispute_id} by {user['email']}")
    
    return {"message": "Response added successfully", "timeline_entry": timeline_entry}

@api_router.put("/disputes/{dispute_id}/status")
async def update_dispute_status(
    dispute_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Update dispute status (admin only for most statuses)"""
    body = await request.json()
    new_status = body.get("status")
    notes = body.get("notes", "")
    
    if new_status not in [DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW, DisputeStatus.AWAITING_RESPONSE,
                          DisputeStatus.ESCALATED, DisputeStatus.RESOLVED, DisputeStatus.CLOSED]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    dispute = await db.disputes.find_one({"dispute_id": dispute_id}, {"_id": 0})
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    # Only admin can escalate or change to certain statuses
    is_admin = user["role"] == UserRole.ADMIN
    if not is_admin and new_status in [DisputeStatus.ESCALATED, DisputeStatus.UNDER_REVIEW]:
        raise HTTPException(status_code=403, detail="Only admin can set this status")
    
    now = datetime.now(timezone.utc).isoformat()
    
    timeline_entry = {
        "event": "status_changed",
        "message": f"Status changed from {dispute['status']} to {new_status}" + (f": {notes}" if notes else ""),
        "user_id": user["user_id"],
        "user_name": user["name"],
        "user_role": "admin" if is_admin else ("buyer" if dispute.get("buyer_id") == user["user_id"] else "vendor"),
        "timestamp": now,
        "old_status": dispute["status"],
        "new_status": new_status
    }
    
    # Set priority for escalated disputes
    update_data = {
        "status": new_status,
        "updated_at": now
    }
    if new_status == DisputeStatus.ESCALATED:
        update_data["priority"] = "high"
    
    await db.disputes.update_one(
        {"dispute_id": dispute_id},
        {
            "$push": {"timeline": timeline_entry},
            "$set": update_data
        }
    )
    
    logger.info(f"Dispute {dispute_id} status changed to {new_status} by {user['email']}")
    
    return {"message": f"Status updated to {new_status}", "timeline_entry": timeline_entry}

@api_router.put("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    resolution_data: DisputeResolve,
    user: dict = Depends(get_current_user)
):
    """Resolve a dispute (admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Only admin can resolve disputes")
    
    dispute = await db.disputes.find_one({"dispute_id": dispute_id}, {"_id": 0})
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    if dispute["status"] in [DisputeStatus.RESOLVED, DisputeStatus.CLOSED]:
        raise HTTPException(status_code=400, detail="Dispute is already resolved or closed")
    
    now = datetime.now(timezone.utc).isoformat()
    
    timeline_entry = {
        "event": "dispute_resolved",
        "message": f"Dispute resolved: {resolution_data.resolution_type.replace('_', ' ').title()}. {resolution_data.resolution_notes}",
        "user_id": user["user_id"],
        "user_name": user["name"],
        "user_role": "admin",
        "timestamp": now,
        "resolution_type": resolution_data.resolution_type,
        "refund_amount": resolution_data.refund_amount
    }
    
    await db.disputes.update_one(
        {"dispute_id": dispute_id},
        {
            "$push": {"timeline": timeline_entry},
            "$set": {
                "status": DisputeStatus.RESOLVED,
                "resolution_type": resolution_data.resolution_type,
                "resolution_notes": resolution_data.resolution_notes,
                "refund_amount": resolution_data.refund_amount,
                "resolved_by": user["user_id"],
                "resolved_at": now,
                "updated_at": now
            }
        }
    )
    
    # Update order
    await db.orders.update_one(
        {"order_id": dispute.get("order_id")},
        {"$set": {"dispute_resolved": True, "dispute_resolution": resolution_data.resolution_type}}
    )
    
    # Notify both parties
    for party_id in [dispute.get("buyer_id"), dispute.get("vendor_id")]:
        if party_id:
            notification = {
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "user_id": party_id,
                "type": "dispute_resolved",
                "title": "Dispute Resolved",
                "message": f"Dispute #{dispute_id[:12]} has been resolved: {resolution_data.resolution_type.replace('_', ' ').title()}",
                "data": {"dispute_id": dispute_id, "resolution_type": resolution_data.resolution_type},
                "is_read": False,
                "created_at": now
            }
            await db.notifications.insert_one(notification)
    
    # Send email notification
    buyer = await db.users.find_one({"user_id": dispute.get("buyer_id")}, {"_id": 0, "email": 1, "name": 1})
    if buyer:
        resolution_email = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #059669 0%, #047857 100%); padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0;">Dispute Resolved</h2>
            </div>
            <div style="padding: 25px; background: #f8fafc;">
                <p>Hello {buyer.get("name", "User")},</p>
                <p>Your dispute <strong>#{dispute_id[:12]}</strong> has been resolved.</p>
                <div style="background: white; border-radius: 8px; padding: 16px; margin: 20px 0; border-left: 4px solid #059669;">
                    <p style="margin: 0 0 8px 0;"><strong>Resolution:</strong> {resolution_data.resolution_type.replace('_', ' ').title()}</p>
                    <p style="margin: 0 0 8px 0;"><strong>Notes:</strong> {resolution_data.resolution_notes}</p>
                    {f'<p style="margin: 0;"><strong>Refund Amount:</strong> ₹{resolution_data.refund_amount:,.2f}</p>' if resolution_data.refund_amount else ''}
                </div>
                <p>If you have any questions, please contact our support team.</p>
            </div>
        </div>
        '''
        asyncio.create_task(send_email_async(buyer["email"], f"Dispute Resolved - #{dispute_id[:12]}", resolution_email))
    
    logger.info(f"Dispute {dispute_id} resolved by admin {user['email']}: {resolution_data.resolution_type}")
    
    return {"message": "Dispute resolved successfully", "resolution_type": resolution_data.resolution_type}

@api_router.get("/orders/{order_id}/dispute")
async def get_order_dispute(order_id: str, user: dict = Depends(get_current_user)):
    """Get dispute for a specific order"""
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check authorization
    is_buyer = order.get("buyer_id") == user["user_id"]
    is_vendor = order.get("vendor_id") == user["user_id"]
    is_admin = user["role"] == UserRole.ADMIN
    
    if not (is_buyer or is_vendor or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    dispute = await db.disputes.find_one({"order_id": order_id}, {"_id": 0})
    
    return {"dispute": dispute, "has_dispute": dispute is not None}

# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "OEMLinker API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ============== NOTIFICATIONS ==============

@api_router.get("/notifications")
async def get_notifications(limit: int = 20, unread_only: bool = False, user: dict = Depends(get_current_user)):
    """Get user's notifications"""
    query = {"user_id": user["user_id"]}
    if unread_only:
        query["is_read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    unread_count = await db.notifications.count_documents({
        "user_id": user["user_id"], 
        "is_read": False
    })
    
    return {
        "notifications": notifications,
        "unread_count": unread_count
    }

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": user["user_id"]},
        {"$set": {"is_read": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    result = await db.notifications.update_many(
        {"user_id": user["user_id"], "is_read": False},
        {"$set": {"is_read": True}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}

@api_router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str, user: dict = Depends(get_current_user)):
    """Delete a notification"""
    result = await db.notifications.delete_one({
        "notification_id": notification_id, 
        "user_id": user["user_id"]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}

# ============== VOICE AGENT ENDPOINTS ==============

# Initialize voice agent components
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

@api_router.post("/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Transcribe audio to text using OpenAI Whisper - supports all Indian languages"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="Voice agent not configured")
    
    try:
        # Read audio file
        audio_bytes = await audio.read()
        audio_file = BytesIO(audio_bytes)
        audio_file.name = audio.filename or "audio.webm"
        
        # Initialize STT
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        
        # Transcribe with auto language detection (supports Hindi, Tamil, Telugu, Bengali, etc.)
        response = await stt.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="verbose_json"  # Get language detection
        )
        
        # Extract detected language
        detected_language = getattr(response, 'language', 'en') or 'en'
        
        return {
            "text": response.text,
            "language": detected_language
        }
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@api_router.post("/voice/query")
async def voice_query(request: Request, user: dict = Depends(get_current_user)):
    """Process voice query and return matched RFQs with audio response - supports all Indian languages"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="Voice agent not configured")
    
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Voice agent is only available for vendors")
    
    body = await request.json()
    query_text = body.get("query", "")
    detected_language = body.get("language", "en")  # Language detected from transcription
    
    # Map language codes to full names for AI prompt
    LANGUAGE_NAMES = {
        "en": "English",
        "hi": "Hindi (हिंदी)",
        "ta": "Tamil (தமிழ்)",
        "te": "Telugu (తెలుగు)",
        "bn": "Bengali (বাংলা)",
        "mr": "Marathi (मराठी)",
        "gu": "Gujarati (ગુજરાતી)",
        "kn": "Kannada (ಕನ್ನಡ)",
        "ml": "Malayalam (മലയാളം)",
        "pa": "Punjabi (ਪੰਜਾਬੀ)",
        "or": "Odia (ଓଡ଼ିଆ)",
        "as": "Assamese (অসমীয়া)",
        "ur": "Urdu (اردو)"
    }
    
    language_name = LANGUAGE_NAMES.get(detected_language, "the same language as the user's query")
    
    if not query_text:
        raise HTTPException(status_code=400, detail="Query text is required")
    
    try:
        # Get vendor info
        vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if not vendor:
            no_profile_msg = {
                "en": "Your vendor profile is not set up yet. Please complete your profile first.",
                "hi": "आपकी वेंडर प्रोफ़ाइल अभी तक सेट नहीं हुई है। कृपया पहले अपनी प्रोफ़ाइल पूरी करें।",
            }
            return {
                "response_text": no_profile_msg.get(detected_language, no_profile_msg["en"]),
                "matched_rfqs": [],
                "audio_base64": None,
                "language": detected_language
            }
        
        # Get matched RFQs for this vendor - only open, non-quoted, non-expired
        now = datetime.now(timezone.utc).isoformat()
        
        # First get all RFQs where this vendor is matched
        matched_rfqs = await db.rfqs.find(
            {
                "matched_vendors.vendor_id": vendor["vendor_id"],
                "status": {"$in": ["matching", "open", "published"]},  # Only open statuses
                "$or": [
                    {"deadline": {"$exists": False}},
                    {"deadline": None},
                    {"deadline": ""},
                    {"deadline": {"$gte": now}}  # Not expired
                ]
            },
            {"_id": 0, "rfq_id": 1, "title": 1, "material_type": 1, "quantity": 1, 
             "tolerance": 1, "matched_vendors": 1, "created_at": 1, "deadline": 1}
        ).sort("created_at", -1).to_list(50)
        
        # Get quotes submitted by this vendor to filter out already quoted RFQs
        vendor_quotes = await db.quotes.find(
            {"vendor_id": vendor["vendor_id"]},
            {"_id": 0, "rfq_id": 1}
        ).to_list(1000)
        quoted_rfq_ids = set(q["rfq_id"] for q in vendor_quotes)
        
        # Filter to get this vendor's match info - exclude already quoted RFQs
        rfq_summaries = []
        for rfq in matched_rfqs:
            # Skip if vendor already quoted this RFQ
            if rfq["rfq_id"] in quoted_rfq_ids:
                continue
                
            vendor_match = next((v for v in rfq.get("matched_vendors", []) if v.get("vendor_id") == vendor["vendor_id"]), None)
            if vendor_match:
                # Check deadline
                deadline = rfq.get("deadline")
                is_expired = False
                if deadline:
                    try:
                        if isinstance(deadline, str) and deadline:
                            deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                            is_expired = deadline_dt < datetime.now(timezone.utc)
                    except:
                        pass
                
                if not is_expired:
                    rfq_summaries.append({
                        "rfq_id": rfq["rfq_id"],
                        "title": rfq["title"],
                        "material": rfq.get("material_type", "Not specified"),
                        "quantity": rfq.get("quantity", "N/A"),
                        "match_score": vendor_match.get("suitability_score", 0),
                        "matching_machines": vendor_match.get("matching_machines", [])[:2],
                        "created_at": rfq.get("created_at", ""),
                        "deadline": rfq.get("deadline", "")
                    })
        
        # Build context for AI - with multilingual support
        language_instruction = f"\n\nIMPORTANT: Respond ONLY in {language_name}. Do not mix languages."
        
        if rfq_summaries:
            rfq_context = "\n".join([
                f"- {r['title']}: {r['material']}, Qty: {r['quantity']}, Match Score: {r['match_score']}%, Machines: {', '.join(r['matching_machines'][:2]) or 'Compatible'}"
                for r in rfq_summaries[:5]
            ])
            system_prompt = f"""You are a helpful voice assistant for OEMLinker, a manufacturing marketplace.
The vendor has {len(rfq_summaries)} OPEN RFQs waiting for quotes. These are active opportunities that have not been quoted yet and are not expired.
Here are the most recent ones:
{rfq_context}

Respond naturally and concisely to the vendor's question. Keep responses under 100 words.
Focus on the most relevant information. Mention match scores and encourage them to submit quotes.{language_instruction}"""
        else:
            system_prompt = f"""You are a helpful voice assistant for OEMLinker, a manufacturing marketplace.
The vendor currently has no open RFQs waiting for quotes. This could mean:
1. They have already quoted on all matched RFQs
2. No new matching opportunities at the moment
Encourage them to check back soon for new opportunities.
Keep responses friendly and under 50 words.{language_instruction}"""
        
        # Use AI to generate natural response
        session_id = f"voice_{user['user_id']}_{uuid.uuid4().hex[:8]}"
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_prompt
        ).with_model("openai", "gpt-4o-mini")
        
        response_text = await chat.send_message(UserMessage(text=query_text))
        
        # Generate audio response
        tts = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
        audio_base64 = await tts.generate_speech_base64(
            text=response_text,
            model="tts-1",
            voice="nova"  # Energetic, upbeat voice - works well for multiple languages
        )
        
        return {
            "response_text": response_text,
            "matched_rfqs": rfq_summaries[:5],
            "total_matches": len(rfq_summaries),
            "audio_base64": audio_base64,
            "language": detected_language
        }
        
    except Exception as e:
        logger.error(f"Voice query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Voice query failed: {str(e)}")

@api_router.post("/voice/speak")
async def text_to_speech(request: Request, user: dict = Depends(get_current_user)):
    """Convert text to speech"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="Voice agent not configured")
    
    body = await request.json()
    text = body.get("text", "")
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    if len(text) > 4096:
        raise HTTPException(status_code=400, detail="Text too long. Maximum 4096 characters.")
    
    try:
        tts = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
        audio_base64 = await tts.generate_speech_base64(
            text=text,
            model="tts-1",
            voice="nova"
        )
        
        return {"audio_base64": audio_base64}
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")

# ============== WHATSAPP INTEGRATION (GUPSHUP) ==============
# Import WhatsApp service
from app.services.whatsapp_service import whatsapp_service, parse_webhook_message

# Store WhatsApp conversation sessions
whatsapp_sessions = {}  # {phone_number: {"user_id": str, "conversation": [], "last_active": datetime}}

# Store pending registrations awaiting confirmation
pending_registrations = {}  # {phone_number: {"gstin": str, "gst_data": dict, "expires_at": datetime}}
PENDING_REGISTRATION_TTL_MINUTES = 10  # Pending registration expires after 10 minutes

# Store pending machine additions awaiting dimensions
pending_machines = {}  # {phone_number: {"machine_info": dict, "step": str, "dimensions": dict, "image_url": str, "expires_at": datetime}}
PENDING_MACHINE_TTL_MINUTES = 15  # Pending machine flow expires after 15 minutes

# Indian State to Language Mapping for WhatsApp localization
STATE_LANGUAGE_MAP = {
    # Hindi Belt
    "Delhi": {"lang": "Hindi", "code": "hi"},
    "Uttar Pradesh": {"lang": "Hindi", "code": "hi"},
    "Madhya Pradesh": {"lang": "Hindi", "code": "hi"},
    "Bihar": {"lang": "Hindi", "code": "hi"},
    "Rajasthan": {"lang": "Hindi", "code": "hi"},
    "Haryana": {"lang": "Hindi", "code": "hi"},
    "Uttarakhand": {"lang": "Hindi", "code": "hi"},
    "Jharkhand": {"lang": "Hindi", "code": "hi"},
    "Chhattisgarh": {"lang": "Hindi", "code": "hi"},
    "Himachal Pradesh": {"lang": "Hindi", "code": "hi"},
    # South India
    "Tamil Nadu": {"lang": "Tamil", "code": "ta"},
    "Karnataka": {"lang": "Kannada", "code": "kn"},
    "Kerala": {"lang": "Malayalam", "code": "ml"},
    "Andhra Pradesh": {"lang": "Telugu", "code": "te"},
    "Telangana": {"lang": "Telugu", "code": "te"},
    # West India
    "Maharashtra": {"lang": "Marathi", "code": "mr"},
    "Gujarat": {"lang": "Gujarati", "code": "gu"},
    "Goa": {"lang": "Konkani", "code": "kok"},
    # East India
    "West Bengal": {"lang": "Bengali", "code": "bn"},
    "Odisha": {"lang": "Odia", "code": "or"},
    "Assam": {"lang": "Assamese", "code": "as"},
    # North India
    "Punjab": {"lang": "Punjabi", "code": "pa"},
    "Jammu and Kashmir": {"lang": "Urdu", "code": "ur"},
    # Default
    "default": {"lang": "Hindi", "code": "hi"}
}

# Bilingual dimension prompts - English + Regional Language
DIMENSION_PROMPTS_BILINGUAL = {
    # Hindi translations
    "hi": {
        "max_thickness": "अधिकतम मोटाई (mm)?",
        "max_length": "अधिकतम लंबाई (mm)?",
        "amperage": "अधिकतम एम्पेयर (A)?",
        "max_x": "X-अक्ष ट्रैवल (mm)?",
        "max_y": "Y-अक्ष ट्रैवल (mm)?",
        "max_z": "Z-अक्ष ट्रैवल (mm)?",
        "max_diameter": "अधिकतम व्यास (mm)?",
        "bore_diameter": "स्पिंडल बोर व्यास (mm)?",
        "table_diameter": "टेबल व्यास (mm)?",
        "max_weight": "अधिकतम वजन (kg)?",
        "table_size_x": "टेबल साइज़ X (mm)?",
        "table_size_y": "टेबल साइज़ Y (mm)?",
        "pallet_size": "पैलेट साइज़ (mm)?",
        "spindle_bore": "स्पिंडल बोर (mm)?",
        "max_swing": "अधिकतम स्विंग (mm)?",
        "max_stroke": "अधिकतम स्ट्रोक (mm)?",
        "stroke": "स्ट्रोक (mm)?",
        "tonnage": "टनेज (ton)?",
        "laser_power": "लेजर पावर (kW)?",
        "max_temp": "अधिकतम तापमान (°C)?",
        "accuracy": "सटीकता (μm)?",
        "layer_thickness": "लेयर मोटाई (μm)?",
        "max_taper_angle": "अधिकतम टेपर एंगल (°)?",
        "max_module": "अधिकतम मॉड्यूल (mm)?",
        "min_teeth": "न्यूनतम दांत?",
        "a_axis_range": "A-अक्ष रेंज (°)?",
        "c_axis_range": "C-अक्ष रेंज (°)?",
        "spindle_travel": "स्पिंडल ट्रैवल (mm)?",
        "arm_length": "आर्म लंबाई (mm)?",
        "max_depth": "अधिकतम गहराई (mm)?",
        "skip": "छोड़ें",
        "or_skip": "(या 'skip' टाइप करें)"
    },
    # Marathi translations
    "mr": {
        "max_thickness": "कमाल जाडी (mm)?",
        "max_length": "कमाल लांबी (mm)?",
        "amperage": "कमाल अँपिअर (A)?",
        "max_x": "X-अक्ष ट्रॅव्हल (mm)?",
        "max_y": "Y-अक्ष ट्रॅव्हल (mm)?",
        "max_z": "Z-अक्ष ट्रॅव्हल (mm)?",
        "max_diameter": "कमाल व्यास (mm)?",
        "max_weight": "कमाल वजन (kg)?",
        "tonnage": "टनेज (ton)?",
        "skip": "वगळा",
        "or_skip": "(किंवा 'skip' टाइप करा)"
    },
    # Gujarati translations
    "gu": {
        "max_thickness": "મહત્તમ જાડાઈ (mm)?",
        "max_length": "મહત્તમ લંબાઈ (mm)?",
        "amperage": "મહત્તમ એમ્પિયર (A)?",
        "max_x": "X-અક્ષ ટ્રાવેલ (mm)?",
        "max_y": "Y-અક્ષ ટ્રાવેલ (mm)?",
        "max_z": "Z-અક્ષ ટ્રાવેલ (mm)?",
        "max_diameter": "મહત્તમ વ્યાસ (mm)?",
        "max_weight": "મહત્તમ વજન (kg)?",
        "skip": "છોડો",
        "or_skip": "(અથવા 'skip' ટાઇપ કરો)"
    },
    # Tamil translations
    "ta": {
        "max_thickness": "அதிகபட்ச தடிமன் (mm)?",
        "max_length": "அதிகபட்ச நீளம் (mm)?",
        "amperage": "அதிகபட்ச ஆம்பியர் (A)?",
        "max_x": "X-அச்சு பயணம் (mm)?",
        "max_y": "Y-அச்சு பயணம் (mm)?",
        "max_z": "Z-அச்சு பயணம் (mm)?",
        "max_diameter": "அதிகபட்ச விட்டம் (mm)?",
        "max_weight": "அதிகபட்ச எடை (kg)?",
        "skip": "தவிர்",
        "or_skip": "(அல்லது 'skip' தட்டச்சு செய்யவும்)"
    },
    # Telugu translations
    "te": {
        "max_thickness": "గరిష్ట మందం (mm)?",
        "max_length": "గరిష్ట పొడవు (mm)?",
        "amperage": "గరిష్ట ఆంపియర్ (A)?",
        "max_x": "X-అక్షం ట్రావెల్ (mm)?",
        "max_y": "Y-అక్షం ట్రావెల్ (mm)?",
        "max_z": "Z-అక్షం ట్రావెల్ (mm)?",
        "max_diameter": "గరిష్ట వ్యాసం (mm)?",
        "max_weight": "గరిష్ట బరువు (kg)?",
        "skip": "దాటవేయి",
        "or_skip": "(లేదా 'skip' టైప్ చేయండి)"
    },
    # Kannada translations
    "kn": {
        "max_thickness": "ಗರಿಷ್ಠ ದಪ್ಪ (mm)?",
        "max_length": "ಗರಿಷ್ಠ ಉದ್ದ (mm)?",
        "amperage": "ಗರಿಷ್ಠ ಆಂಪಿಯರ್ (A)?",
        "max_x": "X-ಅಕ್ಷ ಪ್ರಯಾಣ (mm)?",
        "max_y": "Y-ಅಕ್ಷ ಪ್ರಯಾಣ (mm)?",
        "max_z": "Z-ಅಕ್ಷ ಪ್ರಯಾಣ (mm)?",
        "max_diameter": "ಗರಿಷ್ಠ ವ್ಯಾಸ (mm)?",
        "max_weight": "ಗರಿಷ್ಠ ತೂಕ (kg)?",
        "skip": "ಬಿಡಿ",
        "or_skip": "(ಅಥವಾ 'skip' ಟೈಪ್ ಮಾಡಿ)"
    },
    # Bengali translations
    "bn": {
        "max_thickness": "সর্বোচ্চ পুরুত্ব (mm)?",
        "max_length": "সর্বোচ্চ দৈর্ঘ্য (mm)?",
        "amperage": "সর্বোচ্চ অ্যাম্পিয়ার (A)?",
        "max_x": "X-অক্ষ ট্রাভেল (mm)?",
        "max_y": "Y-অক্ষ ট্রাভেল (mm)?",
        "max_z": "Z-অক্ষ ট্রাভেল (mm)?",
        "max_diameter": "সর্বোচ্চ ব্যাস (mm)?",
        "max_weight": "সর্বোচ্চ ওজন (kg)?",
        "skip": "এড়িয়ে যান",
        "or_skip": "(অথবা 'skip' টাইপ করুন)"
    },
    # Punjabi translations
    "pa": {
        "max_thickness": "ਵੱਧ ਤੋਂ ਵੱਧ ਮੋਟਾਈ (mm)?",
        "max_length": "ਵੱਧ ਤੋਂ ਵੱਧ ਲੰਬਾਈ (mm)?",
        "amperage": "ਵੱਧ ਤੋਂ ਵੱਧ ਐਂਪੀਅਰ (A)?",
        "max_x": "X-ਧੁਰਾ ਟ੍ਰੈਵਲ (mm)?",
        "max_y": "Y-ਧੁਰਾ ਟ੍ਰੈਵਲ (mm)?",
        "max_z": "Z-ਧੁਰਾ ਟ੍ਰੈਵਲ (mm)?",
        "max_diameter": "ਵੱਧ ਤੋਂ ਵੱਧ ਵਿਆਸ (mm)?",
        "max_weight": "ਵੱਧ ਤੋਂ ਵੱਧ ਭਾਰ (kg)?",
        "skip": "ਛੱਡੋ",
        "or_skip": "(ਜਾਂ 'skip' ਟਾਈਪ ਕਰੋ)"
    }
}

# Bilingual messages for all WhatsApp flows - English + Regional Language
WHATSAPP_MESSAGES_BILINGUAL = {
    "hi": {
        # Welcome & Registration
        "welcome": "OEMLinker में आपका स्वागत है!",
        "welcome_vendor": "स्वागत है",
        "registration": "वेंडर रजिस्ट्रेशन",
        "send_gst": "अपना GST सर्टिफिकेट भेजें (फोटो या PDF)",
        "gst_found": "GST विवरण मिले",
        "confirm_details": "क्या ये विवरण सही हैं?",
        "type_yes": "'हाँ' टाइप करें पुष्टि के लिए",
        "type_no": "'नहीं' टाइप करें रद्द करने के लिए",
        "registration_success": "रजिस्ट्रेशन सफल!",
        "registration_failed": "रजिस्ट्रेशन विफल",
        "registration_cancelled": "रजिस्ट्रेशन रद्द",
        
        # Machine flow
        "machine_identified": "मशीन पहचानी गई!",
        "add_dimensions": "अब आयाम जोड़ें:",
        "machine_saved": "मशीन सफलतापूर्वक सेव हुई!",
        "machine_cancelled": "मशीन जोड़ना रद्द",
        "send_machine_photo": "मशीन की फोटो भेजें",
        "no_machines": "अभी तक कोई मशीन नहीं जोड़ी गई",
        "your_machines": "आपकी मशीनें",
        
        # Commands
        "help": "सहायता",
        "available_commands": "उपलब्ध कमांड:",
        "status": "स्थिति",
        "profile": "प्रोफाइल",
        "machines": "मशीनें",
        "quotes": "कोटेशन",
        
        # Status messages  
        "processing": "प्रोसेस हो रहा है...",
        "please_wait": "कृपया प्रतीक्षा करें",
        "error_occurred": "कोई त्रुटि हुई",
        "try_again": "कृपया पुनः प्रयास करें",
        "not_understood": "समझ नहीं आया",
        
        # Confirmations
        "yes": "हाँ",
        "no": "नहीं",
        "confirm": "पुष्टि करें",
        "cancel": "रद्द करें",
        "skip": "छोड़ें",
        "done": "पूर्ण",
        
        # Profile
        "company_name": "कंपनी का नाम",
        "phone": "फोन",
        "state": "राज्य",
        "city": "शहर",
        "machines_count": "मशीनों की संख्या",
        
        # Quotes & RFQ
        "new_rfq": "नया RFQ मिला!",
        "quote_submitted": "कोटेशन जमा हुआ",
        "pending_quotes": "लंबित कोटेशन",
        "no_quotes": "कोई कोटेशन नहीं"
    },
    "mr": {
        "welcome": "OEMLinker मध्ये आपले स्वागत आहे!",
        "welcome_vendor": "स्वागत आहे",
        "registration": "विक्रेता नोंदणी",
        "send_gst": "तुमचे GST प्रमाणपत्र पाठवा (फोटो किंवा PDF)",
        "gst_found": "GST तपशील सापडले",
        "confirm_details": "हे तपशील बरोबर आहेत का?",
        "type_yes": "पुष्टीसाठी 'होय' टाइप करा",
        "type_no": "रद्द करण्यासाठी 'नाही' टाइप करा",
        "registration_success": "नोंदणी यशस्वी!",
        "registration_failed": "नोंदणी अयशस्वी",
        "registration_cancelled": "नोंदणी रद्द",
        "machine_identified": "मशीन ओळखली!",
        "add_dimensions": "आता परिमाण जोडा:",
        "machine_saved": "मशीन यशस्वीरित्या सेव्ह झाली!",
        "machine_cancelled": "मशीन जोडणे रद्द",
        "send_machine_photo": "मशीनचा फोटो पाठवा",
        "no_machines": "अद्याप कोणतीही मशीन जोडली नाही",
        "your_machines": "तुमच्या मशीन्स",
        "help": "मदत",
        "available_commands": "उपलब्ध आदेश:",
        "status": "स्थिती",
        "profile": "प्रोफाइल",
        "machines": "मशीन्स",
        "quotes": "कोटेशन",
        "processing": "प्रक्रिया सुरू आहे...",
        "please_wait": "कृपया प्रतीक्षा करा",
        "error_occurred": "त्रुटी आली",
        "try_again": "कृपया पुन्हा प्रयत्न करा",
        "not_understood": "समजले नाही",
        "yes": "होय",
        "no": "नाही",
        "confirm": "पुष्टी करा",
        "cancel": "रद्द करा",
        "skip": "वगळा",
        "done": "पूर्ण",
        "company_name": "कंपनीचे नाव",
        "phone": "फोन",
        "state": "राज्य",
        "city": "शहर",
        "machines_count": "मशीनची संख्या",
        "new_rfq": "नवीन RFQ आला!",
        "quote_submitted": "कोटेशन सबमिट झाले",
        "pending_quotes": "प्रलंबित कोटेशन",
        "no_quotes": "कोणतेही कोटेशन नाही"
    },
    "gu": {
        "welcome": "OEMLinker માં આપનું સ્વાગત છે!",
        "welcome_vendor": "સ્વાગત છે",
        "registration": "વિક્રેતા નોંધણી",
        "send_gst": "તમારું GST પ્રમાણપત્ર મોકલો (ફોટો અથવા PDF)",
        "gst_found": "GST વિગતો મળી",
        "confirm_details": "શું આ વિગતો સાચી છે?",
        "type_yes": "પુષ્ટિ માટે 'હા' ટાઇપ કરો",
        "type_no": "રદ કરવા માટે 'ના' ટાઇપ કરો",
        "registration_success": "નોંધણી સફળ!",
        "registration_failed": "નોંધણી નિષ્ફળ",
        "registration_cancelled": "નોંધણી રદ",
        "machine_identified": "મશીન ઓળખાઈ!",
        "add_dimensions": "હવે પરિમાણો ઉમેરો:",
        "machine_saved": "મશીન સફળતાપૂર્વક સેવ થઈ!",
        "machine_cancelled": "મશીન ઉમેરવું રદ",
        "send_machine_photo": "મશીનનો ફોટો મોકલો",
        "no_machines": "હજુ સુધી કોઈ મશીન ઉમેરાઈ નથી",
        "your_machines": "તમારી મશીનો",
        "help": "મદદ",
        "available_commands": "ઉપલબ્ધ આદેશો:",
        "processing": "પ્રક્રિયા થઈ રહી છે...",
        "error_occurred": "ભૂલ થઈ",
        "try_again": "કૃપા કરીને ફરી પ્રયાસ કરો",
        "not_understood": "સમજાયું નહીં",
        "yes": "હા",
        "no": "ના",
        "skip": "છોડો",
        "done": "પૂર્ણ"
    },
    "ta": {
        "welcome": "OEMLinker-க்கு வரவேற்கிறோம்!",
        "welcome_vendor": "வரவேற்கிறோம்",
        "registration": "விற்பனையாளர் பதிவு",
        "send_gst": "உங்கள் GST சான்றிதழை அனுப்பவும் (புகைப்படம் அல்லது PDF)",
        "gst_found": "GST விவரங்கள் கிடைத்தன",
        "confirm_details": "இந்த விவரங்கள் சரியா?",
        "type_yes": "உறுதிப்படுத்த 'ஆம்' தட்டச்சு செய்யவும்",
        "type_no": "ரத்து செய்ய 'இல்லை' தட்டச்சு செய்யவும்",
        "registration_success": "பதிவு வெற்றிகரமாக!",
        "registration_failed": "பதிவு தோல்வி",
        "registration_cancelled": "பதிவு ரத்து",
        "machine_identified": "இயந்திரம் அடையாளம் காணப்பட்டது!",
        "add_dimensions": "இப்போது பரிமாணங்களை சேர்க்கவும்:",
        "machine_saved": "இயந்திரம் வெற்றிகரமாக சேமிக்கப்பட்டது!",
        "machine_cancelled": "இயந்திரம் சேர்ப்பது ரத்து",
        "send_machine_photo": "இயந்திரத்தின் புகைப்படத்தை அனுப்பவும்",
        "no_machines": "இதுவரை எந்த இயந்திரமும் சேர்க்கப்படவில்லை",
        "your_machines": "உங்கள் இயந்திரங்கள்",
        "help": "உதவி",
        "processing": "செயலாக்கம் நடைபெறுகிறது...",
        "error_occurred": "பிழை ஏற்பட்டது",
        "try_again": "மீண்டும் முயற்சிக்கவும்",
        "not_understood": "புரியவில்லை",
        "yes": "ஆம்",
        "no": "இல்லை",
        "skip": "தவிர்",
        "done": "முடிந்தது"
    },
    "te": {
        "welcome": "OEMLinker కు స్వాగతం!",
        "welcome_vendor": "స్వాగతం",
        "registration": "విక్రేత నమోదు",
        "send_gst": "మీ GST సర్టిఫికేట్ పంపండి (ఫోటో లేదా PDF)",
        "gst_found": "GST వివరాలు దొరికాయి",
        "confirm_details": "ఈ వివరాలు సరైనవా?",
        "type_yes": "నిర్ధారించడానికి 'అవును' టైప్ చేయండి",
        "type_no": "రద్దు చేయడానికి 'కాదు' టైప్ చేయండి",
        "registration_success": "నమోదు విజయవంతం!",
        "registration_failed": "నమోదు విఫలం",
        "registration_cancelled": "నమోదు రద్దు",
        "machine_identified": "మెషిన్ గుర్తించబడింది!",
        "add_dimensions": "ఇప్పుడు కొలతలు జోడించండి:",
        "machine_saved": "మెషిన్ విజయవంతంగా సేవ్ అయింది!",
        "machine_cancelled": "మెషిన్ జోడించడం రద్దు",
        "send_machine_photo": "మెషిన్ ఫోటో పంపండి",
        "no_machines": "ఇంకా మెషిన్లు జోడించబడలేదు",
        "your_machines": "మీ మెషిన్లు",
        "help": "సహాయం",
        "processing": "ప్రాసెస్ అవుతోంది...",
        "error_occurred": "లోపం సంభవించింది",
        "try_again": "దయచేసి మళ్ళీ ప్రయత్నించండి",
        "not_understood": "అర్థం కాలేదు",
        "yes": "అవును",
        "no": "కాదు",
        "skip": "దాటవేయి",
        "done": "పూర్తయింది"
    },
    "kn": {
        "welcome": "OEMLinker ಗೆ ಸ್ವಾಗತ!",
        "welcome_vendor": "ಸ್ವಾಗತ",
        "registration": "ಮಾರಾಟಗಾರ ನೋಂದಣಿ",
        "send_gst": "ನಿಮ್ಮ GST ಪ್ರಮಾಣಪತ್ರವನ್ನು ಕಳುಹಿಸಿ (ಫೋಟೋ ಅಥವಾ PDF)",
        "gst_found": "GST ವಿವರಗಳು ಸಿಕ್ಕಿವೆ",
        "confirm_details": "ಈ ವಿವರಗಳು ಸರಿಯೇ?",
        "type_yes": "ದೃಢೀಕರಿಸಲು 'ಹೌದು' ಟೈಪ್ ಮಾಡಿ",
        "type_no": "ರದ್ದು ಮಾಡಲು 'ಇಲ್ಲ' ಟೈಪ್ ಮಾಡಿ",
        "registration_success": "ನೋಂದಣಿ ಯಶಸ್ವಿ!",
        "registration_failed": "ನೋಂದಣಿ ವಿಫಲ",
        "registration_cancelled": "ನೋಂದಣಿ ರದ್ದು",
        "machine_identified": "ಯಂತ್ರ ಗುರುತಿಸಲಾಗಿದೆ!",
        "add_dimensions": "ಈಗ ಆಯಾಮಗಳನ್ನು ಸೇರಿಸಿ:",
        "machine_saved": "ಯಂತ್ರ ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ!",
        "machine_cancelled": "ಯಂತ್ರ ಸೇರಿಸುವುದು ರದ್ದು",
        "send_machine_photo": "ಯಂತ್ರದ ಫೋಟೋ ಕಳುಹಿಸಿ",
        "no_machines": "ಇನ್ನೂ ಯಾವುದೇ ಯಂತ್ರ ಸೇರಿಸಲಾಗಿಲ್ಲ",
        "your_machines": "ನಿಮ್ಮ ಯಂತ್ರಗಳು",
        "help": "ಸಹಾಯ",
        "processing": "ಪ್ರಕ್ರಿಯೆ ನಡೆಯುತ್ತಿದೆ...",
        "error_occurred": "ದೋಷ ಸಂಭವಿಸಿದೆ",
        "try_again": "ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
        "not_understood": "ಅರ್ಥವಾಗಲಿಲ್ಲ",
        "yes": "ಹೌದು",
        "no": "ಇಲ್ಲ",
        "skip": "ಬಿಡಿ",
        "done": "ಮುಗಿಯಿತು"
    },
    "bn": {
        "welcome": "OEMLinker-এ স্বাগতম!",
        "welcome_vendor": "স্বাগতম",
        "registration": "বিক্রেতা নিবন্ধন",
        "send_gst": "আপনার GST সার্টিফিকেট পাঠান (ছবি বা PDF)",
        "gst_found": "GST বিবরণ পাওয়া গেছে",
        "confirm_details": "এই বিবরণগুলি কি সঠিক?",
        "type_yes": "নিশ্চিত করতে 'হ্যাঁ' টাইপ করুন",
        "type_no": "বাতিল করতে 'না' টাইপ করুন",
        "registration_success": "নিবন্ধন সফল!",
        "registration_failed": "নিবন্ধন ব্যর্থ",
        "registration_cancelled": "নিবন্ধন বাতিল",
        "machine_identified": "মেশিন চিহ্নিত হয়েছে!",
        "add_dimensions": "এখন মাত্রা যোগ করুন:",
        "machine_saved": "মেশিন সফলভাবে সেভ হয়েছে!",
        "machine_cancelled": "মেশিন যোগ করা বাতিল",
        "send_machine_photo": "মেশিনের ছবি পাঠান",
        "no_machines": "এখনও কোনো মেশিন যোগ করা হয়নি",
        "your_machines": "আপনার মেশিনগুলি",
        "help": "সাহায্য",
        "processing": "প্রক্রিয়াকরণ চলছে...",
        "error_occurred": "ত্রুটি ঘটেছে",
        "try_again": "অনুগ্রহ করে আবার চেষ্টা করুন",
        "not_understood": "বুঝতে পারিনি",
        "yes": "হ্যাঁ",
        "no": "না",
        "skip": "এড়িয়ে যান",
        "done": "সম্পন্ন"
    },
    "pa": {
        "welcome": "OEMLinker ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ!",
        "welcome_vendor": "ਸਵਾਗਤ ਹੈ",
        "registration": "ਵਿਕਰੇਤਾ ਰਜਿਸਟ੍ਰੇਸ਼ਨ",
        "send_gst": "ਆਪਣਾ GST ਸਰਟੀਫਿਕੇਟ ਭੇਜੋ (ਫੋਟੋ ਜਾਂ PDF)",
        "gst_found": "GST ਵੇਰਵੇ ਮਿਲੇ",
        "confirm_details": "ਕੀ ਇਹ ਵੇਰਵੇ ਸਹੀ ਹਨ?",
        "type_yes": "ਪੁਸ਼ਟੀ ਲਈ 'ਹਾਂ' ਟਾਈਪ ਕਰੋ",
        "type_no": "ਰੱਦ ਕਰਨ ਲਈ 'ਨਹੀਂ' ਟਾਈਪ ਕਰੋ",
        "registration_success": "ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਸਫਲ!",
        "registration_failed": "ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਅਸਫਲ",
        "registration_cancelled": "ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਰੱਦ",
        "machine_identified": "ਮਸ਼ੀਨ ਪਛਾਣੀ ਗਈ!",
        "add_dimensions": "ਹੁਣ ਮਾਪ ਜੋੜੋ:",
        "machine_saved": "ਮਸ਼ੀਨ ਸਫਲਤਾਪੂਰਵਕ ਸੇਵ ਹੋਈ!",
        "machine_cancelled": "ਮਸ਼ੀਨ ਜੋੜਨਾ ਰੱਦ",
        "send_machine_photo": "ਮਸ਼ੀਨ ਦੀ ਫੋਟੋ ਭੇਜੋ",
        "no_machines": "ਅਜੇ ਕੋਈ ਮਸ਼ੀਨ ਨਹੀਂ ਜੋੜੀ",
        "your_machines": "ਤੁਹਾਡੀਆਂ ਮਸ਼ੀਨਾਂ",
        "help": "ਮਦਦ",
        "processing": "ਪ੍ਰਕਿਰਿਆ ਹੋ ਰਹੀ ਹੈ...",
        "error_occurred": "ਗਲਤੀ ਹੋਈ",
        "try_again": "ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ",
        "not_understood": "ਸਮਝ ਨਹੀਂ ਆਇਆ",
        "yes": "ਹਾਂ",
        "no": "ਨਹੀਂ",
        "skip": "ਛੱਡੋ",
        "done": "ਪੂਰਾ"
    }
}

# Email reminder messages in regional languages
EMAIL_REMINDER_MESSAGES = {
    "hi": {
        "reminder_title": "ईमेल आईडी अपडेट करें",
        "reminder_msg": "कृपया अपना ईमेल आईडी जोड़ें",
        "why_needed": "RFQ मैच और कोटेशन अपडेट के लिए जरूरी",
        "how_to_add": "ईमेल भेजने के लिए 'email' टाइप करें"
    },
    "mr": {
        "reminder_title": "ईमेल आयडी अपडेट करा",
        "reminder_msg": "कृपया तुमचा ईमेल आयडी जोडा",
        "why_needed": "RFQ मॅच आणि कोटेशन अपडेटसाठी आवश्यक",
        "how_to_add": "ईमेल पाठवण्यासाठी 'email' टाइप करा"
    },
    "gu": {
        "reminder_title": "ઈમેલ આઈડી અપડેટ કરો",
        "reminder_msg": "કૃપા કરીને તમારો ઈમેલ આઈડી ઉમેરો",
        "why_needed": "RFQ મેચ અને કોટેશન અપડેટ માટે જરૂરી",
        "how_to_add": "ઈમેલ મોકલવા માટે 'email' ટાઈપ કરો"
    },
    "ta": {
        "reminder_title": "மின்னஞ்சல் ஐடி புதுப்பிக்கவும்",
        "reminder_msg": "தயவுசெய்து உங்கள் மின்னஞ்சல் ஐடி சேர்க்கவும்",
        "why_needed": "RFQ பொருத்தம் மற்றும் மேற்கோள் புதுப்பிப்புகளுக்கு தேவை",
        "how_to_add": "மின்னஞ்சல் அனுப்ப 'email' தட்டச்சு செய்யவும்"
    },
    "te": {
        "reminder_title": "ఇమెయిల్ ఐడి అప్‌డేట్ చేయండి",
        "reminder_msg": "దయచేసి మీ ఇమెయిల్ ఐడి జోడించండి",
        "why_needed": "RFQ మ్యాచ్ మరియు కొటేషన్ అప్‌డేట్‌లకు అవసరం",
        "how_to_add": "ఇమెయిల్ పంపడానికి 'email' టైప్ చేయండి"
    },
    "kn": {
        "reminder_title": "ಇಮೇಲ್ ಐಡಿ ಅಪ್‌ಡೇಟ್ ಮಾಡಿ",
        "reminder_msg": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಇಮೇಲ್ ಐಡಿ ಸೇರಿಸಿ",
        "why_needed": "RFQ ಹೊಂದಾಣಿಕೆ ಮತ್ತು ಕೋಟೇಶನ್ ಅಪ್‌ಡೇಟ್‌ಗಳಿಗೆ ಅಗತ್ಯ",
        "how_to_add": "ಇಮೇಲ್ ಕಳುಹಿಸಲು 'email' ಟೈಪ್ ಮಾಡಿ"
    },
    "bn": {
        "reminder_title": "ইমেল আইডি আপডেট করুন",
        "reminder_msg": "অনুগ্রহ করে আপনার ইমেল আইডি যোগ করুন",
        "why_needed": "RFQ ম্যাচ এবং কোটেশন আপডেটের জন্য প্রয়োজনীয়",
        "how_to_add": "ইমেল পাঠাতে 'email' টাইপ করুন"
    },
    "pa": {
        "reminder_title": "ਈਮੇਲ ਆਈਡੀ ਅੱਪਡੇਟ ਕਰੋ",
        "reminder_msg": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਈਮੇਲ ਆਈਡੀ ਜੋੜੋ",
        "why_needed": "RFQ ਮੈਚ ਅਤੇ ਕੋਟੇਸ਼ਨ ਅੱਪਡੇਟਸ ਲਈ ਜ਼ਰੂਰੀ",
        "how_to_add": "ਈਮੇਲ ਭੇਜਣ ਲਈ 'email' ਟਾਈਪ ਕਰੋ"
    }
}

# Email reminder interval in hours (send reminder every 24 hours)
EMAIL_REMINDER_INTERVAL_HOURS = 24

# Store pending email inputs
pending_email_inputs = {}  # {phone_number: {"expires_at": datetime}}

async def check_and_send_email_reminder(vendor: dict, user: dict) -> Optional[str]:
    """Check if vendor needs email reminder and return reminder message if needed"""
    if not vendor or not user:
        return None
    
    # Check if user already has a valid email (not phone number)
    user_email = user.get("email", "")
    # Phone-based logins use phone number as email field
    if user.get("phone_login") or (user_email and user_email.isdigit() and len(user_email) == 10):
        # User registered via WhatsApp and doesn't have real email
        pass
    elif user_email and "@" in user_email:
        # User has valid email, no reminder needed
        return None
    
    # Also check vendor contact_email
    if vendor.get("contact_email") and "@" in vendor.get("contact_email", ""):
        return None
    
    # Check when last reminder was sent
    last_reminder = vendor.get("email_reminder_sent_at")
    if last_reminder:
        try:
            if isinstance(last_reminder, str):
                last_reminder_dt = datetime.fromisoformat(last_reminder.replace('Z', '+00:00'))
            else:
                last_reminder_dt = last_reminder
            
            hours_since_reminder = (datetime.now(timezone.utc) - last_reminder_dt).total_seconds() / 3600
            if hours_since_reminder < EMAIL_REMINDER_INTERVAL_HOURS:
                return None  # Not yet time for another reminder
        except:
            pass  # If parsing fails, send reminder
    
    # Update last reminder time
    await db.vendors.update_one(
        {"vendor_id": vendor["vendor_id"]},
        {"$set": {"email_reminder_sent_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get bilingual reminder message
    lang_info = get_vendor_language(vendor)
    lang_code = lang_info.get("code", "hi")
    messages = EMAIL_REMINDER_MESSAGES.get(lang_code, EMAIL_REMINDER_MESSAGES.get("hi", {}))
    
    reminder = f"""
📧 *{messages.get('reminder_title', 'Update Email ID')}*
_{messages.get('reminder_msg', 'Please add your email ID')}_

⚠️ Email is required for:
• Receiving RFQ match notifications
• Getting quotation updates
• Important platform alerts

_{messages.get('why_needed', 'Required for RFQ match and quotation updates')}_

👉 Type *email* to add your email ID
_{messages.get('how_to_add', "Type 'email' to send your email")}_
"""
    return reminder.strip()

async def process_email_input(sender: str, text: str, vendor: dict, user: dict) -> Optional[str]:
    """Process email input from vendor"""
    import re
    
    # Check if we're expecting email input
    if sender not in pending_email_inputs:
        return None
    
    pending = pending_email_inputs[sender]
    
    # Check if expired
    if datetime.now(timezone.utc) > pending["expires_at"]:
        del pending_email_inputs[sender]
        return None
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    email = text.strip().lower()
    
    if not re.match(email_pattern, email):
        lang_info = get_vendor_language(vendor)
        return f"""❌ *Invalid Email Format*

Please enter a valid email address.
Example: yourname@company.com

_{get_bilingual_message("try_again", vendor)}_"""
    
    # Check if email already exists for another user (check contact_email, not login email)
    existing = await db.users.find_one({
        "contact_email": email, 
        "user_id": {"$ne": user["user_id"]}
    })
    if existing:
        return f"""❌ *Email Already Registered*

This email is already associated with another account.
Please use a different email address."""
    
    # Update user contact_email only (DO NOT change login email for phone_login users)
    # The phone number in 'email' field is their login ID - preserve it
    user_update = {"contact_email": email}
    
    # Only update primary email if user does NOT have phone_login
    if not user.get("phone_login"):
        user_update["email"] = email
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": user_update}
    )
    
    # Update vendor contact email
    await db.vendors.update_one(
        {"vendor_id": vendor["vendor_id"]},
        {"$set": {"contact_email": email, "email_updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Remove from pending
    del pending_email_inputs[sender]
    
    # Get bilingual success message
    lang_info = get_vendor_language(vendor)
    lang_code = lang_info.get("code", "hi")
    
    success_messages = {
        "hi": "ईमेल सफलतापूर्वक अपडेट हुआ!",
        "mr": "ईमेल यशस्वीरित्या अपडेट झाले!",
        "gu": "ઈમેલ સફળતાપૂર્વક અપડેટ થયો!",
        "ta": "மின்னஞ்சல் வெற்றிகரமாக புதுப்பிக்கப்பட்டது!",
        "te": "ఇమెయిల్ విజయవంతంగా అప్‌డేట్ చేయబడింది!",
        "kn": "ಇಮೇಲ್ ಯಶಸ್ವಿಯಾಗಿ ಅಪ್‌ಡೇಟ್ ಆಯಿತು!",
        "bn": "ইমেল সফলভাবে আপডেট হয়েছে!",
        "pa": "ਈਮੇਲ ਸਫਲਤਾਪੂਰਵਕ ਅੱਪਡੇਟ ਹੋਈ!"
    }
    
    regional_success = success_messages.get(lang_code, success_messages["hi"])
    
    return f"""✅ *Email Updated Successfully!*
_{regional_success}_

📧 Your email: *{email}*

You will now receive:
• RFQ match notifications
• Quotation updates
• Platform alerts

Thank you for updating your profile! 🎉"""

def get_bilingual_message(key: str, vendor: dict, fallback: str = "") -> str:
    """Get bilingual message (English line will be added by caller, this returns regional translation)"""
    if not vendor:
        return ""
    
    lang_info = get_vendor_language(vendor)
    lang_code = lang_info.get("code", "hi")
    
    messages = WHATSAPP_MESSAGES_BILINGUAL.get(lang_code, WHATSAPP_MESSAGES_BILINGUAL.get("hi", {}))
    regional_text = messages.get(key, "")
    
    if regional_text:
        return f"\n_{regional_text}_"
    return ""

def format_bilingual(english_text: str, message_key: str, vendor: dict) -> str:
    """Format a complete bilingual message with English + Regional language"""
    regional = get_bilingual_message(message_key, vendor)
    if regional:
        return f"{english_text}{regional}"
    return english_text

def get_vendor_language(vendor: dict) -> dict:
    """Get language info based on vendor's state"""
    if not vendor:
        return STATE_LANGUAGE_MAP["default"]
    
    state = vendor.get("state", "")
    if not state:
        # Try to get from address or GST state code
        address = vendor.get("address", "") or ""
        # Check for state names in address
        for state_name in STATE_LANGUAGE_MAP:
            if state_name != "default" and state_name.lower() in address.lower():
                return STATE_LANGUAGE_MAP[state_name]
        return STATE_LANGUAGE_MAP["default"]
    
    # Normalize state name
    state_normalized = state.strip().title()
    return STATE_LANGUAGE_MAP.get(state_normalized, STATE_LANGUAGE_MAP["default"])

def get_bilingual_prompt(field_key: str, english_prompt: str, vendor: dict) -> str:
    """Generate bilingual prompt (English + Regional Language)"""
    lang_info = get_vendor_language(vendor)
    lang_code = lang_info.get("code", "hi")
    lang_name = lang_info.get("lang", "Hindi")
    
    # Get regional translation
    regional_prompts = DIMENSION_PROMPTS_BILINGUAL.get(lang_code, DIMENSION_PROMPTS_BILINGUAL.get("hi", {}))
    regional_prompt = regional_prompts.get(field_key, "")
    
    # Check if this is an optional field (contains 'skip')
    is_optional = "skip" in english_prompt.lower()
    skip_text = regional_prompts.get("or_skip", "(या 'skip' टाइप करें)")
    
    if regional_prompt:
        if is_optional:
            return f"{english_prompt}\n_{regional_prompt}_ {skip_text}"
        else:
            return f"{english_prompt}\n_{regional_prompt}_"
    else:
        return english_prompt

# Dimension fields by machine category - ALIGNED WITH /api/machine-categories endpoint
# Each field now includes "key", "label", and "type" to match web app structure
MACHINE_DIMENSION_FIELDS = {
    "CNC Turning/Lathe": {
        "fields": [
            {"key": "max_length", "label": "Max Turning Length (mm)", "prompt": "What is the *max turning length* (mm)?"},
            {"key": "max_diameter", "label": "Max Turning Diameter (mm)", "prompt": "What is the *max turning diameter* (mm)?"},
            {"key": "max_swing", "label": "Max Swing Over Bed (mm)", "prompt": "What is the *max swing over bed* (mm)? (or type 'skip')"}
        ]
    },
    "VTL (Vertical Turret Lathe)": {
        "fields": [
            {"key": "max_diameter", "label": "Max Turning Diameter (mm)", "prompt": "What is the *max turning diameter* (mm)?"},
            {"key": "max_length", "label": "Max Turning Height (mm)", "prompt": "What is the *max turning height* (mm)?"},
            {"key": "table_diameter", "label": "Table Diameter (mm)", "prompt": "What is the *table diameter* (mm)?"},
            {"key": "max_weight", "label": "Max Workpiece Weight (kg)", "prompt": "What is the *max workpiece weight* (kg)? (or type 'skip')"}
        ]
    },
    "VMC (Vertical Machining Center)": {
        "fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "prompt": "What is the *X-axis travel* (mm)?"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "prompt": "What is the *Y-axis travel* (mm)?"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "prompt": "What is the *Z-axis travel* (mm)?"},
            {"key": "table_size_x", "label": "Table Size X (mm)", "prompt": "What is the *table size X* (mm)? (or type 'skip')"},
            {"key": "table_size_y", "label": "Table Size Y (mm)", "prompt": "What is the *table size Y* (mm)? (or type 'skip')"}
        ]
    },
    "HMC (Horizontal Machining Center)": {
        "fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "prompt": "What is the *X-axis travel* (mm)?"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "prompt": "What is the *Y-axis travel* (mm)?"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "prompt": "What is the *Z-axis travel* (mm)?"},
            {"key": "pallet_size", "label": "Pallet Size (mm)", "prompt": "What is the *pallet size* (mm)? (or type 'skip')"}
        ]
    },
    "5-Axis Machining": {
        "fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "prompt": "What is the *X-axis travel* (mm)?"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "prompt": "What is the *Y-axis travel* (mm)?"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "prompt": "What is the *Z-axis travel* (mm)?"},
            {"key": "max_diameter", "label": "Max Part Diameter (mm)", "prompt": "What is the *max part diameter* (mm)?"},
            {"key": "a_axis_range", "label": "A-Axis Range (°)", "prompt": "What is the *A-axis range* (degrees)? (or type 'skip')"},
            {"key": "c_axis_range", "label": "C-Axis Range (°)", "prompt": "What is the *C-axis range* (degrees)? (or type 'skip')"}
        ]
    },
    "Conventional Lathe": {
        "fields": [
            {"key": "max_length", "label": "Center Distance (mm)", "prompt": "What is the *center distance* (mm)?"},
            {"key": "max_diameter", "label": "Swing Over Bed (mm)", "prompt": "What is the *swing over bed* (mm)?"},
            {"key": "spindle_bore", "label": "Spindle Bore (mm)", "prompt": "What is the *spindle bore* (mm)? (or type 'skip')"}
        ]
    },
    "Conventional Milling": {
        "fields": [
            {"key": "max_x", "label": "Table Travel X (mm)", "prompt": "What is the *table travel X* (mm)?"},
            {"key": "max_y", "label": "Table Travel Y (mm)", "prompt": "What is the *table travel Y* (mm)?"},
            {"key": "max_z", "label": "Head Travel Z (mm)", "prompt": "What is the *head travel Z* (mm)?"},
            {"key": "table_size_x", "label": "Table Size X (mm)", "prompt": "What is the *table size X* (mm)? (or type 'skip')"},
            {"key": "table_size_y", "label": "Table Size Y (mm)", "prompt": "What is the *table size Y* (mm)? (or type 'skip')"}
        ]
    },
    "Boring Machine": {
        "fields": [
            {"key": "bore_diameter", "label": "Max Spindle Diameter (mm)", "prompt": "What is the *max spindle diameter* (mm)?"},
            {"key": "max_x", "label": "X-Axis Travel (mm)", "prompt": "What is the *X-axis travel* (mm)?"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "prompt": "What is the *Y-axis travel* (mm)?"},
            {"key": "max_z", "label": "Z-Axis/Spindle Travel (mm)", "prompt": "What is the *Z-axis/spindle travel* (mm)? (or type 'skip')"}
        ]
    },
    "Shaping Machine": {
        "fields": [
            {"key": "max_stroke", "label": "Max Stroke Length (mm)", "prompt": "What is the *max stroke length* (mm)?"},
            {"key": "max_x", "label": "Table Travel X (mm)", "prompt": "What is the *table travel X* (mm)?"},
            {"key": "max_y", "label": "Table Travel Y (mm)", "prompt": "What is the *table travel Y* (mm)?"},
            {"key": "table_size_x", "label": "Table Size X (mm)", "prompt": "What is the *table size X* (mm)? (or type 'skip')"}
        ]
    },
    "Gear Manufacturing": {
        "fields": [
            {"key": "max_diameter", "label": "Max Gear Diameter (mm)", "prompt": "What is the *max gear diameter* (mm)?"},
            {"key": "max_module", "label": "Max Module (mm)", "prompt": "What is the *max module* (mm)?"},
            {"key": "max_length", "label": "Max Face Width (mm)", "prompt": "What is the *max face width* (mm)?"},
            {"key": "min_teeth", "label": "Min No. of Teeth", "prompt": "What is the *min number of teeth*? (or type 'skip')"}
        ]
    },
    "Grinding": {
        "fields": [
            {"key": "max_x", "label": "Table Travel/Length (mm)", "prompt": "What is the *table travel/length* (mm)?"},
            {"key": "max_y", "label": "Table Width (mm)", "prompt": "What is the *table width* (mm)?"},
            {"key": "max_diameter", "label": "Max Grinding Diameter (mm)", "prompt": "What is the *max grinding diameter* (mm)?"},
            {"key": "max_length", "label": "Max Grinding Length (mm)", "prompt": "What is the *max grinding length* (mm)? (or type 'skip')"}
        ]
    },
    "EDM": {
        "fields": [
            {"key": "max_x", "label": "X-Axis Travel (mm)", "prompt": "What is the *X-axis travel* (mm)?"},
            {"key": "max_y", "label": "Y-Axis Travel (mm)", "prompt": "What is the *Y-axis travel* (mm)?"},
            {"key": "max_z", "label": "Z-Axis Travel (mm)", "prompt": "What is the *Z-axis travel* (mm)?"},
            {"key": "max_taper_angle", "label": "Max Taper Angle (°)", "prompt": "What is the *max taper angle* (degrees)? (or type 'skip')"},
            {"key": "max_thickness", "label": "Max Workpiece Thickness (mm)", "prompt": "What is the *max workpiece thickness* (mm)? (or type 'skip')"}
        ]
    },
    "Drilling Machine": {
        "fields": [
            {"key": "max_diameter", "label": "Max Drilling Diameter (mm)", "prompt": "What is the *max drilling diameter* (mm)?"},
            {"key": "max_depth", "label": "Max Drilling Depth (mm)", "prompt": "What is the *max drilling depth* (mm)?"},
            {"key": "spindle_travel", "label": "Spindle Travel (mm)", "prompt": "What is the *spindle travel* (mm)?"},
            {"key": "arm_length", "label": "Radial Arm Length (mm)", "prompt": "What is the *radial arm length* (mm)? (or type 'skip')"}
        ]
    },
    "Laser Cutting": {
        "fields": [
            {"key": "max_x", "label": "Cutting Area X (mm)", "prompt": "What is the *cutting area X* (mm)?"},
            {"key": "max_y", "label": "Cutting Area Y (mm)", "prompt": "What is the *cutting area Y* (mm)?"},
            {"key": "max_thickness", "label": "Max Cutting Thickness (mm)", "prompt": "What is the *max cutting thickness* (mm)?"},
            {"key": "laser_power", "label": "Laser Power (kW)", "prompt": "What is the *laser power* (kW)? (or type 'skip')"}
        ]
    },
    "Plasma/Waterjet Cutting": {
        "fields": [
            {"key": "max_x", "label": "Cutting Area X (mm)", "prompt": "What is the *cutting area X* (mm)?"},
            {"key": "max_y", "label": "Cutting Area Y (mm)", "prompt": "What is the *cutting area Y* (mm)?"},
            {"key": "max_thickness", "label": "Max Cutting Thickness (mm)", "prompt": "What is the *max cutting thickness* (mm)? (or type 'skip')"}
        ]
    },
    "Sheet Metal/Press": {
        "fields": [
            {"key": "max_length", "label": "Bed Length (mm)", "prompt": "What is the *bed length* (mm)?"},
            {"key": "max_thickness", "label": "Max Sheet Thickness (mm)", "prompt": "What is the *max sheet thickness* (mm)?"},
            {"key": "tonnage", "label": "Tonnage/Press Force (ton)", "prompt": "What is the *tonnage/press force* (ton)?"},
            {"key": "stroke", "label": "Stroke (mm)", "prompt": "What is the *stroke* (mm)? (or type 'skip')"}
        ]
    },
    "Welding": {
        "fields": [
            {"key": "max_thickness", "label": "Max Weld Thickness (mm)", "prompt": "What is the *max weld thickness* (mm)?"},
            {"key": "max_length", "label": "Max Weld Length (mm)", "prompt": "What is the *max weld length* (mm)?"},
            {"key": "amperage", "label": "Max Amperage (A)", "prompt": "What is the *max amperage* (A)? (or type 'skip')"}
        ]
    },
    "Heat Treatment": {
        "fields": [
            {"key": "max_x", "label": "Chamber Length (mm)", "prompt": "What is the *chamber length* (mm)?"},
            {"key": "max_y", "label": "Chamber Width (mm)", "prompt": "What is the *chamber width* (mm)?"},
            {"key": "max_z", "label": "Chamber Height (mm)", "prompt": "What is the *chamber height* (mm)?"},
            {"key": "max_temp", "label": "Max Temperature (°C)", "prompt": "What is the *max temperature* (°C)? (or type 'skip')"}
        ]
    },
    "Surface Treatment": {
        "fields": [
            {"key": "max_x", "label": "Max Part Length (mm)", "prompt": "What is the *max part length* (mm)?"},
            {"key": "max_y", "label": "Max Part Width (mm)", "prompt": "What is the *max part width* (mm)?"},
            {"key": "max_z", "label": "Max Part Height (mm)", "prompt": "What is the *max part height* (mm)?"},
            {"key": "max_weight", "label": "Max Part Weight (kg)", "prompt": "What is the *max part weight* (kg)? (or type 'skip')"}
        ]
    },
    "Inspection/CMM": {
        "fields": [
            {"key": "max_x", "label": "Measuring Range X (mm)", "prompt": "What is the *measuring range X* (mm)?"},
            {"key": "max_y", "label": "Measuring Range Y (mm)", "prompt": "What is the *measuring range Y* (mm)?"},
            {"key": "max_z", "label": "Measuring Range Z (mm)", "prompt": "What is the *measuring range Z* (mm)?"},
            {"key": "accuracy", "label": "Accuracy (μm)", "prompt": "What is the *accuracy* (μm)? (or type 'skip')"}
        ]
    },
    "Additive Manufacturing": {
        "fields": [
            {"key": "max_x", "label": "Build Volume X (mm)", "prompt": "What is the *build volume X* (mm)?"},
            {"key": "max_y", "label": "Build Volume Y (mm)", "prompt": "What is the *build volume Y* (mm)?"},
            {"key": "max_z", "label": "Build Volume Z (mm)", "prompt": "What is the *build volume Z* (mm)?"},
            {"key": "layer_thickness", "label": "Min Layer Thickness (μm)", "prompt": "What is the *min layer thickness* (μm)? (or type 'skip')"}
        ]
    },
    # Default fallback for categories not explicitly listed
    "default": {
        "fields": [
            {"key": "max_x", "label": "Max X Dimension (mm)", "prompt": "What is the *max X dimension* (mm)?"},
            {"key": "max_y", "label": "Max Y Dimension (mm)", "prompt": "What is the *max Y dimension* (mm)?"},
            {"key": "max_z", "label": "Max Z Dimension (mm)", "prompt": "What is the *max Z dimension* (mm)? (or type 'skip')"}
        ]
    }
}

def get_dimension_config_for_category(category: str) -> dict:
    """Get dimension configuration for a machine category with fuzzy matching."""
    # Exact match first
    if category in MACHINE_DIMENSION_FIELDS:
        return MACHINE_DIMENSION_FIELDS[category]
    
    # Try partial/fuzzy match
    category_lower = category.lower()
    for config_key in MACHINE_DIMENSION_FIELDS:
        if config_key.lower() in category_lower or category_lower in config_key.lower():
            return MACHINE_DIMENSION_FIELDS[config_key]
    
    # Special mappings for common AI-identified categories
    category_mappings = {
        "lathe": "CNC Turning/Lathe",
        "turning": "CNC Turning/Lathe",
        "cnc lathe": "CNC Turning/Lathe",
        "vtl": "VTL (Vertical Turret Lathe)",
        "vertical turret": "VTL (Vertical Turret Lathe)",
        "vmc": "VMC (Vertical Machining Center)",
        "vertical machining": "VMC (Vertical Machining Center)",
        "hmc": "HMC (Horizontal Machining Center)",
        "horizontal machining": "HMC (Horizontal Machining Center)",
        "5 axis": "5-Axis Machining",
        "5-axis": "5-Axis Machining",
        "five axis": "5-Axis Machining",
        "milling": "Conventional Milling",
        "cnc milling": "Conventional Milling",
        "boring": "Boring Machine",
        "horizontal boring": "Boring Machine",
        "shaper": "Shaping Machine",
        "planer": "Shaping Machine",
        "gear": "Gear Manufacturing",
        "hobbing": "Gear Manufacturing",
        "grinder": "Grinding",
        "surface grinder": "Grinding",
        "cylindrical grinder": "Grinding",
        "edm": "EDM",
        "wire edm": "EDM",
        "sinker edm": "EDM",
        "drill": "Drilling Machine",
        "radial drill": "Drilling Machine",
        "laser": "Laser Cutting",
        "fiber laser": "Laser Cutting",
        "plasma": "Plasma/Waterjet Cutting",
        "waterjet": "Plasma/Waterjet Cutting",
        "press": "Sheet Metal/Press",
        "press brake": "Sheet Metal/Press",
        "hydraulic press": "Sheet Metal/Press",
        "sheet metal": "Sheet Metal/Press",
        "welding": "Welding",
        "welder": "Welding",
        "weld": "Welding",
        "mig": "Welding",
        "tig": "Welding",
        "arc": "Welding",
        "spot welding": "Welding",
        "esab": "Welding",
        "lincoln": "Welding",
        "fronius": "Welding",
        "miller": "Welding",
        "heat treatment": "Heat Treatment",
        "furnace": "Heat Treatment",
        "hardening": "Heat Treatment",
        "surface treatment": "Surface Treatment",
        "coating": "Surface Treatment",
        "plating": "Surface Treatment",
        "cmm": "Inspection/CMM",
        "inspection": "Inspection/CMM",
        "3d printing": "Additive Manufacturing",
        "additive": "Additive Manufacturing",
        "fdm": "Additive Manufacturing",
        "sla": "Additive Manufacturing",
        "sls": "Additive Manufacturing",
    }
    
    for keyword, mapped_category in category_mappings.items():
        if keyword in category_lower:
            return MACHINE_DIMENSION_FIELDS.get(mapped_category, MACHINE_DIMENSION_FIELDS["default"])
    
    return MACHINE_DIMENSION_FIELDS["default"]

def cleanup_whatsapp_session(phone: str) -> bool:
    """
    Remove WhatsApp session for a given phone number.
    Used when user/vendor is deleted from the platform.
    
    Args:
        phone: Phone number (can be with or without country code)
        
    Returns:
        True if session was found and removed, False otherwise
    """
    if not phone:
        return False
    
    # Normalize phone number
    normalized = phone.replace("+", "").replace(" ", "").replace("-", "")
    last_10 = normalized[-10:] if len(normalized) >= 10 else normalized
    
    # Find and remove matching session
    for session_key in list(whatsapp_sessions.keys()):
        session_last_10 = session_key[-10:] if len(session_key) >= 10 else session_key
        if session_key == normalized or session_last_10 == last_10:
            del whatsapp_sessions[session_key]
            logger.info(f"WhatsApp session removed for phone: {session_key[:6]}***")
            return True
    
    return False

class WhatsAppMessageRequest(BaseModel):
    to_number: str
    message: str

class WhatsAppBroadcastRequest(BaseModel):
    message: str
    vendor_ids: Optional[List[str]] = None  # If None, send to all vendors

@api_router.get("/whatsapp/status")
async def whatsapp_status():
    """Check WhatsApp integration status"""
    is_configured = whatsapp_service.is_configured()
    return {
        "configured": is_configured,
        "app_name": os.environ.get("GUPSHUP_APP_NAME", "OEMLinker"),
        "source_number": os.environ.get("GUPSHUP_SOURCE_NUMBER", "Not configured")[:6] + "****" if os.environ.get("GUPSHUP_SOURCE_NUMBER") else "Not configured"
    }

# WhatsApp Fallback Templates (used when Gupshup API fails)
FALLBACK_TEMPLATES = {
    "machine_upload_reminder": {
        "name": "machine_upload_reminder",
        "description": "Remind vendors to upload their machine photos",
        "content": """Hello Team {0},
📷Send photos of your machines to receive RFQs based on the machines you have.
Or
✏️ Edit details at https://oemlinker.com/vendor/machines
Thanks Team OEMLinker""",
        "parameters": ["company_name"],
        "status": "FALLBACK",
        "category": "utility"
    },
    "rfq_notification": {
        "name": "rfq_notification",
        "description": "Notify vendors about new RFQ matches",
        "content": """Hello {0},
🔔 New RFQ matching your capabilities is available!
Check OEMLinker to view details and submit your quote.
Team OEMLinker""",
        "parameters": ["company_name"],
        "status": "FALLBACK",
        "category": "utility"
    }
}

@api_router.get("/whatsapp/templates")
async def get_whatsapp_templates(
    user: dict = Depends(get_current_user)
):
    """Get approved WhatsApp message templates from Gupshup"""
    if user["role"] != UserRole.ADMIN and not user.get("whatsapp_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not whatsapp_service.is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp service not configured")
    
    # Fetch templates from Gupshup API
    result = await whatsapp_service.get_templates()
    
    if result.get("success") and result.get("templates"):
        return {
            "templates": result["templates"],
            "total": result["total"],
            "source": result.get("source", "gupshup")
        }
    
    # If Gupshup API fails, return fallback templates with warning
    return {
        "templates": list(FALLBACK_TEMPLATES.values()),
        "total": len(FALLBACK_TEMPLATES),
        "source": "fallback",
        "warning": result.get("error", "Could not fetch templates from Gupshup. Showing fallback templates.")
    }

@api_router.post("/whatsapp/send-template")
async def send_whatsapp_template(
    to_number: str,
    template_id: str,
    params: List[str] = [],
    user: dict = Depends(get_current_user)
):
    """Send a WhatsApp template message via Gupshup"""
    if user["role"] != UserRole.ADMIN and not user.get("whatsapp_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not whatsapp_service.is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp service not configured")
    
    # Normalize phone number
    phone = to_number.replace("+", "").replace(" ", "").replace("-", "")
    if not phone.startswith("91") and len(phone) == 10:
        phone = "91" + phone
    
    # Send via Gupshup template API
    result = await whatsapp_service.send_gupshup_template(phone, template_id, params)
    
    if result.get("success"):
        # Store the outgoing message
        vendor = await db.vendors.find_one({"phone": {"$regex": phone[-10:]}}, {"_id": 0})
        await store_whatsapp_message(
            phone=phone,
            direction="outgoing",
            message_type="template",
            content=f"Template: {template_id}",
            vendor_id=vendor.get("vendor_id") if vendor else None,
            vendor_name=vendor.get("company_name") if vendor else None,
            template_name=template_id,
            sent_by=user["user_id"]
        )
        
        return {
            "success": True,
            "message_id": result.get("message_id"),
            "template_id": template_id
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=result.get("error", "Failed to send template")
        )

@api_router.post("/whatsapp/send")
async def send_whatsapp_message(
    data: WhatsAppMessageRequest,
    user: dict = Depends(get_current_user)
):
    """Send a WhatsApp message (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not whatsapp_service.is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp service not configured. Please set GUPSHUP_SOURCE_NUMBER in environment.")
    
    result = await whatsapp_service.send_text_message(data.to_number, data.message)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send message"))
    
    return result

class WhatsAppVoiceRequest(BaseModel):
    to_number: str
    message: str

@api_router.post("/whatsapp/send-voice")
async def send_whatsapp_voice_message(
    data: WhatsAppVoiceRequest,
    user: dict = Depends(get_current_user)
):
    """Send a voice message via WhatsApp (Admin only) - generates TTS and sends audio"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not whatsapp_service.is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp service not configured")
    
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="TTS service not configured")
    
    try:
        # Generate audio from text
        tts = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
        audio_bytes = await tts.generate_speech(
            text=data.message,
            voice="nova"
        )
        
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        # Send audio via WhatsApp
        result = await whatsapp_service.send_audio_message(
            to_number=data.to_number,
            audio_data=audio_bytes,
            file_name="oemlinker_message.mp3"
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to send voice message"))
        
        return {
            "success": True,
            "message_id": result.get("message_id"),
            "audio_size_bytes": len(audio_bytes)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice message error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



# ============== WHATSAPP LOGS ADMIN ENDPOINTS ==============

@api_router.get("/whatsapp/logs")
async def get_whatsapp_logs(
    direction: Optional[str] = None,
    status: Optional[str] = None,
    message_type: Optional[str] = None,
    phone: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    context: Optional[str] = None,
    errors_only: bool = False,
    limit: int = 50,
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    """
    Get WhatsApp message logs with filtering options (Admin only)
    
    Query params:
    - direction: 'outbound' or 'inbound'
    - status: 'sent', 'delivered', 'read', 'failed', 'error'
    - message_type: 'text', 'template', 'image', 'document', 'audio', 'interactive'
    - phone: Filter by phone number (partial match)
    - start_date: Filter from date (YYYY-MM-DD)
    - end_date: Filter to date (YYYY-MM-DD)
    - context: Filter by context (e.g., 'rfq_notification', 'registration')
    - errors_only: Only show failed messages
    - limit: Number of results (max 200)
    - skip: Pagination offset
    """
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.whatsapp_logger import whatsapp_logger
    
    # Validate and cap limit
    limit = min(limit, 200)
    
    result = await whatsapp_logger.get_logs(
        direction=direction,
        status=status,
        message_type=message_type,
        phone=phone,
        start_date=start_date,
        end_date=end_date,
        context=context,
        errors_only=errors_only,
        limit=limit,
        skip=skip
    )
    
    return result


@api_router.get("/whatsapp/logs/stats")
async def get_whatsapp_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get WhatsApp usage statistics (Admin only)
    
    Returns comprehensive statistics including:
    - Total messages (outbound/inbound)
    - Success/failure rates
    - Estimated costs
    - Breakdown by message type
    - Breakdown by context
    - Top errors
    - Daily and hourly trends
    """
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.whatsapp_logger import whatsapp_logger
    
    stats = await whatsapp_logger.get_statistics(
        start_date=start_date,
        end_date=end_date
    )
    
    return stats


@api_router.get("/whatsapp/logs/errors")
async def get_whatsapp_errors(
    days: int = 7,
    user: dict = Depends(get_current_user)
):
    """
    Get WhatsApp error summary for the last N days (Admin only)
    
    Returns grouped errors with counts and sample details
    """
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.whatsapp_logger import whatsapp_logger
    
    # Cap days to prevent expensive queries
    days = min(days, 30)
    
    errors = await whatsapp_logger.get_error_summary(days=days)
    
    return {
        "errors": errors,
        "period_days": days,
        "total_error_types": len(errors)
    }



# ============== ROLE-BASED ACCESS CONTROL (RBAC) ENDPOINTS ==============

class CreateRoleRequest(BaseModel):
    name: str
    description: str
    permissions: List[str]
    color: Optional[str] = "#6b7280"

class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    color: Optional[str] = None

class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str


@api_router.get("/admin/permissions")
async def get_all_permissions(user: dict = Depends(get_current_user)):
    """Get all available permissions grouped by module (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    return {
        "permissions": rbac_service.get_all_permissions(),
        "permissions_list": rbac_service.get_permissions_list()
    }


@api_router.get("/admin/roles")
async def get_all_roles(
    include_base_roles: bool = True,
    user: dict = Depends(get_current_user)
):
    """Get all roles (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    roles = await rbac_service.get_all_roles(include_base_roles=include_base_roles)
    return {"roles": roles, "total": len(roles)}


@api_router.get("/admin/roles/{role_id}")
async def get_role(role_id: str, user: dict = Depends(get_current_user)):
    """Get a specific role by ID (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    role = await rbac_service.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return role


@api_router.post("/admin/roles")
async def create_role(data: CreateRoleRequest, user: dict = Depends(get_current_user)):
    """Create a new custom role (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    try:
        role = await rbac_service.create_role(
            name=data.name,
            description=data.description,
            permissions=data.permissions,
            color=data.color,
            created_by=user["user_id"]
        )
        return {"success": True, "role": role}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.put("/admin/roles/{role_id}")
async def update_role(
    role_id: str, 
    data: UpdateRoleRequest, 
    user: dict = Depends(get_current_user)
):
    """Update an existing role (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    try:
        role = await rbac_service.update_role(
            role_id=role_id,
            name=data.name,
            description=data.description,
            permissions=data.permissions,
            color=data.color,
            updated_by=user["user_id"]
        )
        return {"success": True, "role": role}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.delete("/admin/roles/{role_id}")
async def delete_role(role_id: str, user: dict = Depends(get_current_user)):
    """Delete a custom role (Admin only, system roles cannot be deleted)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    try:
        await rbac_service.delete_role(role_id)
        return {"success": True, "message": f"Role '{role_id}' deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/admin/roles/assign")
async def assign_role_to_user(data: AssignRoleRequest, user: dict = Depends(get_current_user)):
    """Assign a role to a user (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    try:
        await rbac_service.assign_role_to_user(
            user_id=data.user_id,
            role_id=data.role_id,
            assigned_by=user["user_id"]
        )
        return {"success": True, "message": f"Role '{data.role_id}' assigned to user"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.delete("/admin/roles/assign/{user_id}")
async def remove_role_from_user(user_id: str, user: dict = Depends(get_current_user)):
    """Remove custom role from a user (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    try:
        await rbac_service.remove_role_from_user(user_id)
        return {"success": True, "message": "Custom role removed from user"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.get("/admin/roles/{role_id}/users")
async def get_users_by_role(role_id: str, user: dict = Depends(get_current_user)):
    """Get all users assigned to a role (Admin only)"""
    if not has_admin_access(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.services.rbac_service import rbac_service
    
    users = await rbac_service.get_users_by_role(role_id)
    return {"users": users, "total": len(users)}


@api_router.get("/user/permissions")
async def get_my_permissions(user: dict = Depends(get_current_user)):
    """Get current user's permissions"""
    from app.services.rbac_service import rbac_service
    
    permissions = await rbac_service.get_user_permissions(user["user_id"])
    return {"permissions": permissions, "total": len(permissions)}




# ============== MAGIC LINK WITH REDIRECT HELPER ==============

async def generate_magic_link_for_vendor(phone: str, redirect_url: str = None) -> dict:
    """
    Generate a magic link token for a vendor with optional redirect URL.
    Used internally for WhatsApp RFQ notifications to enable instant login.
    
    Args:
        phone: Vendor's phone number
        redirect_url: Path to redirect to after login (e.g., /vendor/rfq/rfq_123)
    
    Returns:
        dict with success, token, and redirect_url
    """
    try:
        # Normalize phone
        phone_normalized = phone.replace("+", "").replace(" ", "").replace("-", "")
        phone_10digit = phone_normalized[-10:] if len(phone_normalized) >= 10 else phone_normalized
        
        # Find vendor by phone
        vendor = await db.vendors.find_one(
            {"phone": {"$regex": phone_10digit}},
            {"_id": 0, "user_id": 1, "vendor_id": 1}
        )
        
        if not vendor:
            logger.warning(f"Magic link generation failed: Vendor not found for phone {phone_10digit}")
            return {"success": False, "error": "Vendor not found"}
        
        user = await db.users.find_one({"user_id": vendor["user_id"]}, {"_id": 0})
        if not user:
            logger.warning(f"Magic link generation failed: User not found for vendor {vendor['vendor_id']}")
            return {"success": False, "error": "User not found"}
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)  # 30 min expiry
        
        # Validate and sanitize redirect URL - only allow internal paths
        safe_redirect = None
        if redirect_url:
            # Only allow relative paths starting with /
            if redirect_url.startswith("/") and not redirect_url.startswith("//"):
                # Whitelist of allowed redirect patterns
                allowed_patterns = ["/vendor/", "/buyer/", "/admin/", "/dashboard", "/rfq/", "/quotes", "/orders"]
                if any(pattern in redirect_url for pattern in allowed_patterns):
                    safe_redirect = redirect_url
        
        # Store token in MongoDB with redirect URL
        await db.magic_link_tokens.insert_one({
            "token": token,
            "user_id": user["user_id"],
            "phone": phone_normalized,
            "redirect_url": safe_redirect,
            "expires_at": expires_at.isoformat(),
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "rfq_notification"  # Track purpose for analytics
        })
        
        logger.info(f"Magic link generated for vendor {vendor['vendor_id']} with redirect to {safe_redirect}")
        
        return {
            "success": True,
            "token": token,
            "expires_in_minutes": 30,
            "redirect_url": safe_redirect
        }
    except Exception as e:
        logger.error(f"Magic link generation error: {str(e)}")
        return {"success": False, "error": str(e)}



@api_router.post("/whatsapp/notify-rfq")
async def notify_vendors_new_rfq(
    rfq_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Send WhatsApp notifications to matched vendors about a new RFQ
    Sends text message with magic link - drawings are accessed via the platform
    (Meta blocks direct PDF/image attachments as "abusive content")
    """
    if not has_admin_access(user) and user.get("role") != "buyer":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not whatsapp_service.is_configured():
        return {"success": False, "error": "WhatsApp not configured", "notified_count": 0}
    
    # Get RFQ details
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Always use production URL for WhatsApp notifications (vendors access live site)
    BASE_URL = "https://oemlinker.com"
    
    # Check if drawings are available
    drawing_ids = rfq.get("drawing_ids", [])
    has_drawings = len(drawing_ids) > 0
    
    # Get matched vendors with their phone numbers
    notified_count = 0
    errors = []
    
    for match in rfq.get("matched_vendors", []):
        vendor_id = match.get("vendor_id")
        if not vendor_id:
            continue
        
        vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})
        if not vendor or not vendor.get("phone"):
            continue
        
        phone = vendor.get("phone", "").strip()
        if not phone:
            continue
        
        company_name = vendor.get("company_name", "Partner")
        part_name = rfq.get("title", "New Part")[:50]
        
        # Get recommended process from AI analysis
        ai_analysis = rfq.get("ai_analysis") or {}
        processes = ai_analysis.get("recommended_processes") or []
        process_str = ", ".join(processes[:2]) if processes else rfq.get("material_type", "Manufacturing")
        
        quantity = str(rfq.get("quantity", "As Required"))
        
        # Calculate deadline
        deadline_date = rfq.get("deadline")
        if deadline_date:
            try:
                if isinstance(deadline_date, str):
                    deadline_dt = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
                else:
                    deadline_dt = deadline_date
                deadline_str = deadline_dt.strftime("%d %b %Y")
            except:
                deadline_str = "As per RFQ"
        else:
            deadline_str = "As per RFQ"
        
        # Get urgency
        urgency = rfq.get("urgency", "normal")
        urgency_emoji = {"urgent": "🔴", "high": "🟠", "normal": "🟢", "low": "🔵"}.get(urgency, "🟢")
        
        match_score = match.get("suitability_score", match.get("match_score", 0))
        
        # Generate magic link with redirect to RFQ page for instant access
        redirect_path = f"/vendor/rfq/{rfq_id}"
        magic_link_result = await generate_magic_link_for_vendor(phone, redirect_path)
        
        if magic_link_result.get("success"):
            rfq_link = f"{BASE_URL}/magic-login?token={magic_link_result['token']}"
            link_note = "🔑 _Click link for instant access (no login needed)_"
        else:
            rfq_link = f"{BASE_URL}/vendor/rfq/{rfq_id}"
            link_note = "_Login to view and submit quote_"
        
        # Drawing note
        drawing_note = "📎 _Drawings available in the RFQ details_" if has_drawings else ""
        
        # User-friendly notification message
        notification_message = f"""🔔 *New RFQ Match for You!*

Hello *{company_name}*,

A new RFQ matching your capabilities is available.

📋 *{part_name}*
{urgency_emoji} Priority: {urgency.title()}
🔧 Process: {process_str}
📦 Quantity: {quantity}
📅 Deadline: {deadline_str}
🎯 Match Score: {match_score}%

👉 *View RFQ & Submit Quote:*
{rfq_link}

{link_note}
{drawing_note}

Reply *rfqs* to see all opportunities.

_Team OEMLinker_"""

        # Send text message (drawings accessible via the platform link)
        result = await whatsapp_service.send_text_message(
            phone, 
            notification_message,
            context="rfq_vendor_notification",
            vendor_id=vendor_id
        )
        
        if result.get("success"):
            notified_count += 1
            logger.info(f"RFQ notification sent to vendor {vendor_id}")
            
            # Store the notification record
            await store_whatsapp_message(
                phone=phone,
                direction="outgoing",
                message_type="rfq_alert",
                content=f"RFQ Alert: {part_name}",
                vendor_id=vendor_id,
                vendor_name=company_name
            )
        else:
            errors.append({"vendor_id": vendor_id, "error": result.get("error")})
            logger.warning(f"Failed to send RFQ notification to {vendor_id}: {result.get('error')}")
    
    return {
        "success": True,
        "notified_count": notified_count,
        "total_matched": len(rfq.get("matched_vendors", [])),
        "errors": errors if errors else None
    }

# Store processed message IDs to prevent duplicates (with TTL)
processed_message_ids = {}  # {message_id: timestamp}
MESSAGE_ID_TTL_SECONDS = 300  # 5 minutes

# Processing locks to prevent concurrent handling for same sender
processing_locks = {}  # {sender: timestamp}
PROCESSING_LOCK_TTL_SECONDS = 30  # Lock expires after 30 seconds

def is_duplicate_message(message_id: str) -> bool:
    """Check if message was already processed (with cleanup of old entries)"""
    if not message_id:
        return False
    
    current_time = datetime.now(timezone.utc).timestamp()
    
    # Cleanup old entries
    expired_ids = [mid for mid, ts in processed_message_ids.items() 
                   if current_time - ts > MESSAGE_ID_TTL_SECONDS]
    for mid in expired_ids:
        del processed_message_ids[mid]
    
    # Check if already processed
    if message_id in processed_message_ids:
        return True
    
    # Mark as processed
    processed_message_ids[message_id] = current_time
    return False

def acquire_processing_lock(sender: str) -> bool:
    """Acquire a processing lock for a sender to prevent concurrent handling"""
    if not sender:
        return True
    
    current_time = datetime.now(timezone.utc).timestamp()
    
    # Cleanup expired locks
    expired = [s for s, ts in processing_locks.items() 
               if current_time - ts > PROCESSING_LOCK_TTL_SECONDS]
    for s in expired:
        del processing_locks[s]
    
    # Check if already locked
    if sender in processing_locks:
        return False
    
    # Acquire lock
    processing_locks[sender] = current_time
    return True

def release_processing_lock(sender: str):
    """Release the processing lock for a sender"""
    if sender in processing_locks:
        del processing_locks[sender]

@api_router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook endpoint for receiving WhatsApp messages from Gupshup
    Configure this URL in your Gupshup dashboard
    """
    try:
        payload = await request.json()
        logger.info(f"WhatsApp webhook received: {payload.get('type', 'unknown')}")
        logger.info(f"WhatsApp webhook payload: {payload}")  # DEBUG: Log full payload
        
        parsed = parse_webhook_message(payload)
        logger.info(f"WhatsApp parsed message: {parsed}")  # DEBUG: Log parsed result
        
        if not parsed:
            logger.warning("WhatsApp webhook: Could not parse payload")
            return {"status": "ignored"}
        
        if parsed.get("type") == "status":
            # Handle delivery status updates
            logger.info(f"Message status update: {parsed.get('status')} for {parsed.get('message_id')}")
            return {"status": "ok"}
        
        # Check for duplicate message
        message_id = parsed.get("message_id")
        if is_duplicate_message(message_id):
            logger.info(f"Duplicate message ignored: {message_id}")
            return {"status": "duplicate_ignored"}
        
        # Handle incoming message
        sender = parsed.get("sender", "")
        msg_type = parsed.get("type", "text")
        
        # Acquire processing lock to prevent concurrent handling
        if not acquire_processing_lock(sender):
            logger.info(f"Message queued - already processing for: {sender[:6]}***")
            return {"status": "processing"}
        
        try:
            return await _process_whatsapp_message(sender, msg_type, parsed)
        finally:
            release_processing_lock(sender)
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def _process_whatsapp_message(sender: str, msg_type: str, parsed: dict):
    """Internal function to process WhatsApp message - separated for lock management"""
    # Find vendor by phone number
    vendor = await db.vendors.find_one(
        {"phone": {"$regex": sender[-10:]}},  # Match last 10 digits
        {"_id": 0}
    )
    
    user = None
    if vendor:
        user = await db.users.find_one({"user_id": vendor.get("user_id")}, {"_id": 0})
    
    # Store incoming message for admin dashboard
    message_content = ""
    media_url = None
    media_type = None
    filename = None
    
    if msg_type == "text":
        message_content = parsed.get("text", "")
    elif msg_type == "image":
        message_content = f"[Image] {parsed.get('caption', '')}"
        media_url = parsed.get("image_url")
        media_type = parsed.get("mime_type", "image/jpeg")
    elif msg_type == "audio":
        message_content = "[Voice Message]"
        media_url = parsed.get("audio_url")
        media_type = parsed.get("mime_type", "audio/ogg")
    elif msg_type == "video":
        message_content = f"[Video] {parsed.get('caption', '')}"
        media_url = parsed.get("video_url")
        media_type = parsed.get("mime_type", "video/mp4")
    elif msg_type == "document":
        filename = parsed.get("filename", "document")
        message_content = f"[Document] {filename}"
        media_url = parsed.get("document_url")
        media_type = parsed.get("mime_type", "application/octet-stream")
    elif msg_type == "button_reply":
        message_content = f"[Button: {parsed.get('button_title', '')}]"
    
    await store_whatsapp_message(
        phone=sender,
        direction="incoming",
        message_type=msg_type,
        content=message_content,
        vendor_id=vendor.get("vendor_id") if vendor else None,
        vendor_name=vendor.get("company_name") if vendor else None,
        message_id=parsed.get("message_id"),
        media_url=media_url,
        media_type=media_type,
        filename=filename
    )
    
    # Handle voice/audio messages
    if msg_type == "audio" and parsed.get("audio_url"):
        text = await process_voice_message(parsed.get("audio_url"), sender, vendor, user)
        if not text:
            # Failed to transcribe
            if whatsapp_service.is_configured():
                await whatsapp_service.send_text_message(
                    sender, 
                    "⚠️ Sorry, I couldn't understand your voice message. Please try again or type your query."
                )
            return {"status": "ok"}
    # Handle image messages
    elif msg_type == "image" and parsed.get("image_url"):
        # Check if user is already registered - process as machine photo
        if vendor:
            # Check if there's a pending machine - this might be a nameplate image
            # Use normalized phone number matching
            sender_normalized = sender.replace("+", "").replace(" ", "").replace("-", "")
            sender_last10 = sender_normalized[-10:] if len(sender_normalized) >= 10 else sender_normalized
            
            pending_sender_for_image = None
            if sender in pending_machines:
                pending_sender_for_image = sender
            else:
                for key in pending_machines.keys():
                    key_normalized = key.replace("+", "").replace(" ", "").replace("-", "")
                    key_last10 = key_normalized[-10:] if len(key_normalized) >= 10 else key_normalized
                    if key_last10 == sender_last10:
                        pending_sender_for_image = key
                        break
            
            if pending_sender_for_image:
                response_message = await process_nameplate_image(
                    parsed.get("image_url"),
                    pending_sender_for_image,
                    vendor
                )
            else:
                # New machine photo
                response_message = await process_machine_photo_upload(
                    parsed.get("image_url"), 
                    sender, 
                    vendor,
                    parsed.get("caption", "")
                )
            if response_message and whatsapp_service.is_configured():
                await whatsapp_service.send_text_message(sender, response_message)
            return {"status": "ok"}
        
        # Not registered - process image for GST certificate extraction
        response_message = await process_gst_certificate_image(parsed.get("image_url"), sender)
        if response_message and whatsapp_service.is_configured():
            await whatsapp_service.send_text_message(sender, response_message)
        return {"status": "ok"}
    # Handle document messages (PDF GST certificate upload)
    elif msg_type == "document" and parsed.get("document_url"):
        filename = parsed.get("filename", "").lower()
        
        # Check if it's a PDF (likely GST certificate)
        if filename.endswith(".pdf") or "pdf" in filename:
            # Check if user is already registered
            if vendor:
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(
                        sender,
                        "📄 PDF received! You're already registered.\n\nType *help* to see available commands."
                    )
                return {"status": "ok"}
            
            # Process PDF for GST certificate extraction
            logger.info(f"Processing PDF document for GST: {filename}")
            response_message = await process_gst_certificate_document(parsed.get("document_url"), sender, filename)
            if response_message and whatsapp_service.is_configured():
                await whatsapp_service.send_text_message(sender, response_message)
            return {"status": "ok"}
        else:
            # Non-PDF document
            if whatsapp_service.is_configured():
                await whatsapp_service.send_text_message(
                    sender,
                    f"📄 Document received: {filename}\n\nFor GST registration, please upload your GST certificate as:\n• PDF file, OR\n• Image (JPG/PNG)\n\nType *help* for available commands."
                )
            return {"status": "ok"}
    else:
        text = parsed.get("text", "").strip().lower()
    
    if not sender or not text:
        logger.warning(f"WhatsApp: Missing sender or text. Sender: {sender}, Text: '{text}'")
        return {"status": "ok"}
    
    logger.info(f"WhatsApp processing command: '{text}' from {sender[:6]}***")
    
    # Check for pending registration confirmation
    if sender in pending_registrations:
        logger.info(f"Sender {sender[:6]}*** has pending registration")
        pending = pending_registrations[sender]
        
        # Check if expired
        if datetime.now(timezone.utc) > pending["expires_at"]:
            del pending_registrations[sender]
            logger.info(f"Pending registration expired for {sender[:6]}***")
        else:
            # Handle YES/NO confirmation
            text_clean = text.strip().lower()
            if text_clean in ["yes", "y", "confirm", "ok", "haan", "ha", "हां", "हाँ"]:
                # User confirmed - proceed with registration
                del pending_registrations[sender]
                response_message = await process_whatsapp_registration(sender, pending["gstin"])
                if response_message and whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, response_message)
                return {"status": "ok"}
            elif text_clean in ["no", "n", "cancel", "nahi", "nhi", "नहीं"]:
                # User cancelled
                del pending_registrations[sender]
                response_message = """❌ *Registration Cancelled*

Your registration has been cancelled.

To register again:
• Upload your GST certificate image, OR
• Type *register YOUR_GST_NUMBER*

Or register manually at https://oemlinker.com/register"""
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, response_message)
                return {"status": "ok"}
            else:
                # Remind user to confirm
                response_message = f"""⏳ *Confirmation Pending*

You have a pending registration for:
🏢 *{pending['company_name']}*

Please reply:
• *YES* to confirm and register
• *NO* to cancel

This expires in {PENDING_REGISTRATION_TTL_MINUTES} minutes."""
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, response_message)
                return {"status": "ok"}
    
    # Check for pending machine dimension input
    # Normalize sender to handle phone number format differences
    sender_normalized = sender.replace("+", "").replace(" ", "").replace("-", "")
    sender_last10 = sender_normalized[-10:] if len(sender_normalized) >= 10 else sender_normalized
    
    # Check both exact match and normalized match
    pending_sender = None
    if sender in pending_machines:
        pending_sender = sender
    else:
        # Try to find by last 10 digits
        for key in pending_machines.keys():
            key_normalized = key.replace("+", "").replace(" ", "").replace("-", "")
            key_last10 = key_normalized[-10:] if len(key_normalized) >= 10 else key_normalized
            if key_last10 == sender_last10:
                pending_sender = key
                logger.info(f"Found pending_machines by normalized match: '{key}' matches '{sender}'")
                break
    
    logger.info(f"Checking pending_machines for sender: '{sender}', found: {pending_sender is not None}")
    
    if pending_sender:
        logger.info(f"Sender {sender[:6]}*** has pending machine dimension input")
        pending = pending_machines[pending_sender]
        
        # Check if expired
        if datetime.now(timezone.utc) > pending["expires_at"]:
            del pending_machines[pending_sender]
            logger.info(f"Pending machine flow expired for {sender[:6]}***")
            # Continue to normal command processing after expiry
        else:
            text_clean = text.strip().lower()
            
            # Handle skip - save machine without dimensions
            if text_clean in ["skip", "done", "save", "finish"]:
                response_message = await save_pending_machine(pending_sender, vendor)
                del pending_machines[pending_sender]
                if response_message and whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, response_message)
                return {"status": "ok"}
            
            # Handle cancel
            if text_clean in ["cancel", "exit", "quit"]:
                del pending_machines[pending_sender]
                response_message = """❌ *Machine Addition Cancelled*

Send another machine photo to try again."""
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, response_message)
                return {"status": "ok"}
            
            # Handle waiting_for_name step - user is providing machine name
            if pending.get("step") == "waiting_for_name":
                # User provided machine name
                machine_name_input = text.strip()
                
                if len(machine_name_input) < 2:
                    response_message = """⚠️ Please enter a valid machine name.

Example: _Mazak Quick Turn 200_ or _Haas VF-2_

Type *cancel* to abort."""
                    if whatsapp_service.is_configured():
                        await whatsapp_service.send_text_message(sender, response_message)
                    return {"status": "ok"}
                
                # Update machine name
                pending["machine_info"]["name"] = machine_name_input
                
                # Get dimension fields for this machine category
                machine_category = pending["machine_info"]["machine_category"]
                dim_config = get_dimension_config_for_category(machine_category)
                fields_list = dim_config["fields"]
                first_field_info = fields_list[0]
                first_field_key = first_field_info["key"]
                first_prompt_en = first_field_info["prompt"]
                first_prompt = get_bilingual_prompt(first_field_key, first_prompt_en, vendor)
                
                # Update step to start dimension collection
                pending["step"] = first_field_key
                pending["field_index"] = 0
                
                total_fields = len(fields_list)
                fields_preview = ", ".join([f["label"].replace(" (mm)", "").replace(" (kg)", "").replace(" (°)", "").replace(" (μm)", "").replace(" (kW)", "").replace(" (A)", "").replace(" (°C)", "").replace(" (ton)", "") for f in fields_list[:3]])
                if total_fields > 3:
                    fields_preview += f" +{total_fields - 3} more"
                
                # Get bilingual messages
                add_dimensions_regional = get_bilingual_message("add_dimensions", vendor)
                
                response_message = f"""✅ *Machine Name Set!*

🏭 *{machine_name_input}*
📂 Category: {machine_category}
📋 Type: {pending["machine_info"]["machine_type"]}

━━━━━━━━━━━━━━━━━━━━━━
📏 *Now let's add dimensions:*{add_dimensions_regional}
_{fields_preview}_

*Step 1/{total_fields}:*
{first_prompt}

📷 _Or send nameplate photo to auto-fill!_

Type *skip* to save without dimensions."""
                
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, response_message)
                return {"status": "ok"}
            
            # Get current dimension info using the new structure
            machine_category = pending["machine_info"]["machine_category"]
            machine_name = pending["machine_info"].get("name", "Machine")
            
            # Use helper function for fuzzy category matching
            dim_config = get_dimension_config_for_category(machine_category)
            field_index = pending.get("field_index", 0)
            fields_list = dim_config["fields"]
            total_fields = len(fields_list)
            
            # Get current field info from the list
            if field_index < len(fields_list):
                current_field_info = fields_list[field_index]
                current_field_key = current_field_info["key"]
                current_field_label = current_field_info["label"]
                current_prompt_en = current_field_info["prompt"]
                # Get bilingual prompt based on vendor's state
                current_prompt = get_bilingual_prompt(current_field_key, current_prompt_en, vendor)
            else:
                # Should not happen, but fallback
                current_field_key = "max_x"
                current_field_label = "Max X Dimension (mm)"
                current_prompt = "What is the *max X dimension* (mm)?"
            
            # Try to parse dimension value
            try:
                # Extract number from text (handles "500mm", "500 mm", "500", "0.01")
                number_match = re.search(r'[\d.]+', text_clean)
                if number_match:
                    value = float(number_match.group())
                    pending["dimensions"][current_field_key] = value
                    
                    # Move to next field
                    next_index = field_index + 1
                    
                    if next_index < total_fields:
                        # Ask for next dimension with bilingual prompt
                        next_field_info = fields_list[next_index]
                        next_field_key = next_field_info["key"]
                        next_prompt_en = next_field_info["prompt"]
                        next_prompt = get_bilingual_prompt(next_field_key, next_prompt_en, vendor)
                        pending["step"] = next_field_key
                        pending["field_index"] = next_index
                        
                        response_message = f"""✅ *{current_field_label}:* {value}

*Step {next_index + 1}/{total_fields}:*
{next_prompt}

📷 _Or send nameplate photo to auto-fill remaining_
Type *skip* to save machine now."""
                    else:
                        # All dimensions collected - save machine
                        response_message = await save_pending_machine(pending_sender, vendor)
                        del pending_machines[pending_sender]
                    
                    if whatsapp_service.is_configured():
                        await whatsapp_service.send_text_message(sender, response_message)
                    return {"status": "ok"}
                else:
                    # Not a valid number - stay in flow and prompt again
                    response_message = f"""📏 *Adding Dimensions for:* {machine_name}
*Step {field_index + 1}/{total_fields}*

⚠️ Please enter a valid number for *{current_field_label}*

{current_prompt}

Example: _500_ or _500mm_

━━━━━━━━━━━━━━━━━━━━━━
Type *skip* to save without this dimension
Type *cancel* to abort"""
                    if whatsapp_service.is_configured():
                        await whatsapp_service.send_text_message(sender, response_message)
                    return {"status": "ok"}
                    
            except Exception as e:
                logger.error(f"Error processing dimension input: {str(e)}")
                # Stay in flow even on error
                response_message = f"""📏 *Adding Dimensions for:* {machine_name}
*Step {field_index + 1}/{total_fields}*

⚠️ Something went wrong. Please try again.

{current_prompt}

Type *skip* to save without dimensions
Type *cancel* to abort"""
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, response_message)
                return {"status": "ok"}
    
    # Check for pending email input
    if sender in pending_email_inputs:
        pending_email = pending_email_inputs[sender]
        if datetime.now(timezone.utc) > pending_email["expires_at"]:
            del pending_email_inputs[sender]
        else:
            # Process email input
            email_response = await process_email_input(sender, text, vendor, user)
            if email_response:
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(sender, email_response)
                return {"status": "ok"}
    
    # Process commands
    response_message = await process_whatsapp_command(text, sender, vendor, user)
    
    logger.info(f"WhatsApp response generated: {response_message[:100] if response_message else 'None'}...")
    
    # Check if email reminder should be sent (append to response if vendor has no email)
    email_reminder = None
    if vendor and user and response_message:
        email_reminder = await check_and_send_email_reminder(vendor, user)
    
    # Send text response
    if response_message and whatsapp_service.is_configured():
        # Append email reminder if applicable
        if email_reminder:
            response_message = f"{response_message}\n\n━━━━━━━━━━━━━━━━━━━━━━\n{email_reminder}"
        
        send_result = await whatsapp_service.send_text_message(sender, response_message)
        logger.info(f"WhatsApp send result: {send_result}")
        
        # Also send voice response for voice queries
        if msg_type == "audio" and EMERGENT_LLM_KEY:
            try:
                # Generate audio response (shorter version for WhatsApp)
                short_response = response_message[:500] if len(response_message) > 500 else response_message
                # Remove markdown formatting for TTS
                clean_response = short_response.replace("*", "").replace("_", "").replace("`", "")
                
                tts = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
                audio_bytes = await tts.generate_speech(
                    text=clean_response,
                    voice="nova"
                )
                
                if audio_bytes:
                    # Send audio response via WhatsApp
                    audio_result = await whatsapp_service.send_audio_message(
                        to_number=sender,
                        audio_data=audio_bytes,
                        file_name="oemlinker_response.mp3"
                    )
                    
                    if audio_result.get("success"):
                        logger.info(f"Voice response sent to {sender[:6]}***")
                    else:
                        logger.warning(f"Voice response upload failed: {audio_result.get('error')}")
            except Exception as e:
                logger.error(f"TTS generation error: {str(e)}")
    
    # Store conversation for context
    if sender not in whatsapp_sessions:
        whatsapp_sessions[sender] = {
            "user_id": user.get("user_id") if user else None,
            "vendor_id": vendor.get("vendor_id") if vendor else None,
            "conversation": [],
            "last_active": datetime.now(timezone.utc)
        }
    
    whatsapp_sessions[sender]["conversation"].append({
        "role": "user",
        "content": text,
        "type": msg_type,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    whatsapp_sessions[sender]["last_active"] = datetime.now(timezone.utc)
    
    if response_message:
        whatsapp_sessions[sender]["conversation"].append({
            "role": "assistant",
            "content": response_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    return {"status": "ok"}


async def process_voice_message(audio_url: str, sender: str, vendor: Optional[dict], user: Optional[dict]) -> Optional[str]:
    """
    Process voice message: download audio, convert to supported format, transcribe using Whisper, return text
    """
    if not EMERGENT_LLM_KEY:
        logger.warning("Emergent LLM key not configured for voice processing")
        return None
    
    try:
        from app.services.whatsapp_service import download_audio_from_url
        from pydub import AudioSegment
        import tempfile
        import os
        
        # Download audio file
        logger.info(f"Downloading voice message from {audio_url[:50]}...")
        audio_bytes = await download_audio_from_url(audio_url)
        
        if not audio_bytes:
            logger.error("Failed to download audio from Gupshup")
            return None
        
        logger.info(f"Downloaded audio: {len(audio_bytes)} bytes")
        
        # Convert OGG/OPUS to MP3 using pydub (Whisper supports mp3, mp4, wav, webm)
        try:
            # Write original audio to temp file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                temp_ogg.write(audio_bytes)
                temp_ogg_path = temp_ogg.name
            
            # Convert to MP3
            audio = AudioSegment.from_file(temp_ogg_path, format="ogg")
            
            # Export to MP3
            temp_mp3_path = temp_ogg_path.replace('.ogg', '.mp3')
            audio.export(temp_mp3_path, format="mp3")
            
            # Read converted MP3
            with open(temp_mp3_path, 'rb') as f:
                mp3_bytes = f.read()
            
            # Clean up temp files
            os.unlink(temp_ogg_path)
            os.unlink(temp_mp3_path)
            
            logger.info(f"Converted audio to MP3: {len(mp3_bytes)} bytes")
            
        except Exception as conv_error:
            logger.error(f"Audio conversion error: {str(conv_error)}")
            # Try using original bytes as fallback
            mp3_bytes = audio_bytes
        
        # Transcribe using Whisper
        logger.info(f"Transcribing voice message...")
        
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        audio_file = BytesIO(mp3_bytes)
        audio_file.name = "voice_message.mp3"
        
        transcription_result = await stt.transcribe(file=audio_file)
        transcription = transcription_result.text if hasattr(transcription_result, 'text') else str(transcription_result)
        
        if transcription and transcription.strip():
            logger.info(f"Voice transcription successful: '{transcription[:50]}...'")
            
            # Send transcription confirmation to user
            if whatsapp_service.is_configured():
                await whatsapp_service.send_text_message(
                    sender,
                    f"🎤 *Voice query received:*\n_{transcription}_"
                )
            
            return transcription.strip().lower()
        else:
            logger.warning("Empty transcription result")
            return None
            
    except Exception as e:
        logger.error(f"Voice message processing error: {str(e)}")
        return None



async def process_gst_certificate_image(image_url: str, sender: str) -> str:
    """
    Process GST certificate image uploaded via WhatsApp.
    Uses AI Vision to extract GSTIN from the certificate image.
    Shows company details and asks for confirmation before registration.
    
    Args:
        image_url: URL of the uploaded image from Gupshup
        sender: WhatsApp sender phone number
        
    Returns:
        Response message string
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    import base64
    
    try:
        # Download image from Gupshup URL
        logger.info(f"Downloading GST certificate image from: {image_url[:50]}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=30.0)
            if response.status_code != 200:
                logger.error(f"Failed to download image: HTTP {response.status_code}")
                return """⚠️ *Image Download Failed*

Could not download the image. Please try again.

You can also register manually at https://oemlinker.com/register"""
            
            image_data = response.content
        
        # Convert to base64 for AI analysis
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Check if we have the API key
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.error("EMERGENT_LLM_KEY not configured for GST extraction")
            return """⚠️ *Service Unavailable*

AI service is not configured. Please register manually at https://oemlinker.com/register"""
        
        # Use AI Vision to extract GSTIN from the certificate
        chat = LlmChat(
            api_key=api_key,
            session_id=f"gst_extraction_{sender}_{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert at reading Indian GST (Goods and Services Tax) certificates.
            
Your task is to extract the GSTIN (GST Identification Number) from the uploaded GST certificate image.

GSTIN Format: 15 characters - 2 digits (state code) + 10 characters (PAN) + 1 digit (entity code) + 1 character (Z) + 1 check digit
Example: 27AABCU9603R1ZM

IMPORTANT:
- Only extract the GSTIN number, nothing else
- If you can clearly read the GSTIN, respond with ONLY the 15-character GSTIN number
- If the image is not a GST certificate or GSTIN is not visible, respond with "NOT_FOUND"
- If the image is blurry or unclear, respond with "UNCLEAR"
- Do NOT include any other text, explanations, or formatting - just the GSTIN or error code"""
        )
        
        # Create message with image
        user_message = UserMessage(
            text="Please extract the GSTIN number from this GST certificate image.",
            file_contents=[ImageContent(image_base64=image_base64)]
        )
        
        # Get AI response
        ai_response = await chat.send_message(user_message)
        extracted_text = ai_response.strip().upper()
        
        logger.info(f"AI extraction result for {sender[:6]}***: {extracted_text[:20]}...")
        
        # Validate the extracted GSTIN
        if extracted_text == "NOT_FOUND":
            return """⚠️ *GST Certificate Not Detected*

The uploaded image doesn't appear to be a valid GST certificate.

Please upload a clear image of your:
📄 GST Registration Certificate
📄 GST Certificate (Form GST REG-06)

Make sure the GSTIN number is clearly visible.

Or register manually at https://oemlinker.com/register"""
        
        if extracted_text == "UNCLEAR":
            return """⚠️ *Image Not Clear*

The GST number in the image is not clearly visible.

Please upload a clearer image where the *GSTIN number* is easily readable.

Tips:
📸 Ensure good lighting
📸 Avoid shadows on the certificate
📸 Make sure the text is in focus

Or register manually at https://oemlinker.com/register"""
        
        # Validate GSTIN format (15 characters, alphanumeric)
        gstin_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
        if not re.match(gstin_pattern, extracted_text):
            # Try to find GSTIN in the response if AI included extra text
            gstin_match = re.search(r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}Z[0-9A-Z]{1}', extracted_text)
            if gstin_match:
                extracted_text = gstin_match.group()
            else:
                logger.warning(f"Invalid GSTIN format extracted: {extracted_text}")
                return f"""⚠️ *Invalid GST Number*

The extracted number doesn't match GSTIN format.

Extracted: {extracted_text[:20]}...

Please upload a clearer image or type your GST number directly:
Example: *register 27AABCU9603R1ZM*

Or register manually at https://oemlinker.com/register"""
        
        # Check if GST is already registered
        existing_vendor = await db.vendors.find_one({"gstin": extracted_text}, {"_id": 0})
        if existing_vendor:
            return f"""⚠️ *GST Already Registered*

This GST number (*{extracted_text}*) is already linked to a vendor account.

If this is your account, please:
1. Login at https://oemlinker.com/login
2. Update your phone number in profile settings

Or contact support@oemlinker.com for help."""

        # Validate GST using external API and get company details
        GSTIN_API_KEY = os.environ.get("GSTIN_API_KEY", "")
        gst_data = None
        
        if GSTIN_API_KEY:
            try:
                async with httpx.AsyncClient() as client:
                    gst_response = await client.get(
                        f"https://sheet.gstincheck.co.in/check/{GSTIN_API_KEY}/{extracted_text}",
                        timeout=15.0
                    )
                    if gst_response.status_code == 200:
                        result = gst_response.json()
                        if result.get("flag"):
                            gst_data = result.get("data", {})
            except Exception as e:
                logger.warning(f"GST validation API error: {str(e)}")
        
        if not gst_data:
            return f"""⚠️ *GST Validation Failed*

Could not validate GST number: *{extracted_text}*

Please check if:
1. GST number is correct
2. GST is active and valid

You can also register manually at https://oemlinker.com/register"""

        # Extract company details from GST data
        company_name = gst_data.get("tradeNam") or gst_data.get("lgnm", "Unknown Company")
        legal_name = gst_data.get("lgnm", "")
        trade_name = gst_data.get("tradeNam", "")
        gst_status = gst_data.get("sts", "Unknown")
        address = gst_data.get("pradr", {}).get("adr", "")
        city = gst_data.get("pradr", {}).get("loc", "")
        state = gst_data.get("pradr", {}).get("stcd", "")
        pincode = gst_data.get("pradr", {}).get("pncd", "")
        
        # Store pending registration
        pending_registrations[sender] = {
            "gstin": extracted_text,
            "gst_data": gst_data,
            "company_name": company_name,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=PENDING_REGISTRATION_TTL_MINUTES)
        }
        
        logger.info(f"Pending registration stored for {sender[:6]}***: {company_name}")
        
        # Get bilingual messages (use state from GST data for language)
        temp_vendor = {"state": state}
        gst_found_regional = get_bilingual_message("gst_found", temp_vendor)
        confirm_regional = get_bilingual_message("confirm_details", temp_vendor)
        yes_regional = get_bilingual_message("type_yes", temp_vendor)
        no_regional = get_bilingual_message("type_no", temp_vendor)
        
        # Send company details and ask for confirmation
        return f"""📋 *GST Details Found*{gst_found_regional}

Please confirm your company details:
{confirm_regional}

🏢 *Company Name:* {company_name}
📋 *GSTIN:* {extracted_text}
📊 *GST Status:* {gst_status}
📍 *Address:* {address[:50]}{'...' if len(address) > 50 else ''}
🏙️ *City:* {city}
🗺️ *State:* {state}
📮 *Pincode:* {pincode}

━━━━━━━━━━━━━━━━━━━━━━
*Is this information correct?*

Reply *YES* to confirm and register{yes_regional}
Reply *NO* to cancel{no_regional}

⏳ This confirmation expires in {PENDING_REGISTRATION_TTL_MINUTES} minutes."""
        
    except Exception as e:
        logger.error(f"GST certificate processing error: {str(e)}")
        return f"""❌ *Processing Failed*

An error occurred while processing your GST certificate.

Please try again or register manually at https://oemlinker.com/register

You can also type your GST number directly:
*register YOUR_GST_NUMBER*

Contact support@oemlinker.com for assistance."""


async def process_gst_certificate_document(document_url: str, sender: str, filename: str) -> str:
    """
    Process GST certificate PDF uploaded via WhatsApp.
    Downloads PDF, converts to image, and uses AI Vision to extract GSTIN.
    Shows company details and asks for confirmation before registration.
    
    Args:
        document_url: URL of the uploaded PDF from Gupshup
        sender: WhatsApp sender phone number
        filename: Name of the uploaded file
        
    Returns:
        Response message string
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    import base64
    
    try:
        # Send processing message
        if whatsapp_service.is_configured():
            await whatsapp_service.send_text_message(
                sender,
                f"📄 Processing PDF: *{filename}*\n\n⏳ Extracting GST details..."
            )
        
        # Download PDF from Gupshup URL
        logger.info(f"Downloading GST certificate PDF from: {document_url[:50]}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(document_url, timeout=60.0)
            if response.status_code != 200:
                logger.error(f"Failed to download PDF: HTTP {response.status_code}")
                return """⚠️ *PDF Download Failed*

Could not download the PDF. Please try again.

You can also:
• Upload an image of your GST certificate
• Register manually at https://oemlinker.com/register"""
            
            pdf_data = response.content
        
        # Convert PDF to image for AI analysis
        logger.info("Converting PDF to image for analysis...")
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            from io import BytesIO
            
            # Open PDF from bytes
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            
            if pdf_document.page_count == 0:
                return """⚠️ *Empty PDF*

The uploaded PDF appears to be empty.

Please upload a valid GST certificate."""
            
            # Render first page to image (high resolution)
            page = pdf_document[0]
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image then to base64
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG", optimize=True)
            image_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            pdf_document.close()
            
        except ImportError as e:
            logger.error(f"PDF conversion library not available: {str(e)}")
            return """⚠️ *PDF Processing Unavailable*

PDF processing is temporarily unavailable.

Please upload an *image* (JPG/PNG) of your GST certificate instead.

Or register manually at https://oemlinker.com/register"""
        except Exception as e:
            logger.error(f"PDF conversion error: {str(e)}")
            return """⚠️ *PDF Conversion Failed*

Could not process the PDF file.

Please try:
• Upload an image (JPG/PNG) of your GST certificate
• Make sure the PDF is not password protected
• Register manually at https://oemlinker.com/register"""
        
        # Check if we have the API key
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.error("EMERGENT_LLM_KEY not configured for GST extraction")
            return """⚠️ *Service Unavailable*

AI service is not configured. Please register manually at https://oemlinker.com/register"""
        
        # Use AI Vision to extract GSTIN from the certificate
        chat = LlmChat(
            api_key=api_key,
            session_id=f"gst_pdf_extraction_{sender}_{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert at reading Indian GST (Goods and Services Tax) certificates.
            
Your task is to extract the GSTIN (GST Identification Number) from the uploaded GST certificate image.

GSTIN Format: 15 characters - 2 digits (state code) + 10 characters (PAN) + 1 digit (entity code) + 1 character (Z) + 1 check digit
Example: 27AABCU9603R1ZM, 27AAECF7811K1ZF

IMPORTANT:
- Only extract the GSTIN number, nothing else
- If you can clearly read the GSTIN, respond with ONLY the 15-character GSTIN number
- If the image is not a GST certificate or GSTIN is not visible, respond with "NOT_FOUND"
- If the image is blurry or unclear, respond with "UNCLEAR"
- Do NOT include any other text, explanations, or formatting - just the GSTIN or error code"""
        )
        
        # Create message with image
        user_message = UserMessage(
            text="Please extract the GSTIN number from this GST certificate image (converted from PDF).",
            file_contents=[ImageContent(image_base64=image_base64)]
        )
        
        # Get AI response
        ai_response = await chat.send_message(user_message)
        extracted_text = ai_response.strip().upper()
        
        logger.info(f"AI PDF extraction result for {sender[:6]}***: {extracted_text[:20]}...")
        
        # Validate the extracted GSTIN
        if extracted_text == "NOT_FOUND":
            return """⚠️ *GST Certificate Not Detected*

The uploaded PDF doesn't appear to be a valid GST certificate.

Please upload:
📄 GST Registration Certificate (Form GST REG-06)
📄 Or an image where GSTIN is clearly visible

Or register manually at https://oemlinker.com/register"""
        
        if extracted_text == "UNCLEAR":
            return """⚠️ *PDF Not Clear*

Could not read the GST number from the PDF clearly.

Please try:
📸 Upload a clearer PDF
📸 Or upload an image (JPG/PNG) of the certificate

Or register manually at https://oemlinker.com/register"""
        
        # Validate GSTIN format
        gstin_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
        if not re.match(gstin_pattern, extracted_text):
            gstin_match = re.search(r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}Z[0-9A-Z]{1}', extracted_text)
            if gstin_match:
                extracted_text = gstin_match.group()
            else:
                logger.warning(f"Invalid GSTIN format from PDF: {extracted_text}")
                return f"""⚠️ *Invalid GST Number*

Could not extract a valid GSTIN from the PDF.

Extracted: {extracted_text[:20]}...

Please try uploading an image instead, or type:
*register YOUR_GST_NUMBER*

Or register manually at https://oemlinker.com/register"""
        
        # Check if GST is already registered
        existing_vendor = await db.vendors.find_one({"gstin": extracted_text}, {"_id": 0})
        if existing_vendor:
            return f"""⚠️ *GST Already Registered*

This GST number (*{extracted_text}*) is already linked to a vendor account.

If this is your account, please:
1. Login at https://oemlinker.com/login
2. Update your phone number in profile settings

Or contact support@oemlinker.com for help."""

        # Validate GST using external API
        GSTIN_API_KEY = os.environ.get("GSTIN_API_KEY", "")
        gst_data = None
        
        if GSTIN_API_KEY:
            try:
                async with httpx.AsyncClient() as client:
                    gst_response = await client.get(
                        f"https://sheet.gstincheck.co.in/check/{GSTIN_API_KEY}/{extracted_text}",
                        timeout=15.0
                    )
                    if gst_response.status_code == 200:
                        result = gst_response.json()
                        if result.get("flag"):
                            gst_data = result.get("data", {})
            except Exception as e:
                logger.warning(f"GST validation API error: {str(e)}")
        
        if not gst_data:
            return f"""⚠️ *GST Validation Failed*

Could not validate GST number: *{extracted_text}*

Please check if:
1. GST number is correct
2. GST is active and valid

You can also register manually at https://oemlinker.com/register"""

        # Extract company details
        company_name = gst_data.get("tradeNam") or gst_data.get("lgnm", "Unknown Company")
        gst_status = gst_data.get("sts", "Unknown")
        address = gst_data.get("pradr", {}).get("adr", "")
        city = gst_data.get("pradr", {}).get("loc", "")
        state = gst_data.get("pradr", {}).get("stcd", "")
        pincode = gst_data.get("pradr", {}).get("pncd", "")
        
        # Store pending registration
        pending_registrations[sender] = {
            "gstin": extracted_text,
            "gst_data": gst_data,
            "company_name": company_name,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=PENDING_REGISTRATION_TTL_MINUTES)
        }
        
        logger.info(f"Pending registration (from PDF) stored for {sender[:6]}***: {company_name}")
        
        return f"""📋 *GST Details Found (from PDF)*

Please confirm your company details:

🏢 *Company Name:* {company_name}
📋 *GSTIN:* {extracted_text}
📊 *GST Status:* {gst_status}
📍 *Address:* {address[:50]}{'...' if len(address) > 50 else ''}
🏙️ *City:* {city}
🗺️ *State:* {state}
📮 *Pincode:* {pincode}

━━━━━━━━━━━━━━━━━━━━━━
*Is this information correct?*

Reply *YES* to confirm and register
Reply *NO* to cancel

⏳ This confirmation expires in {PENDING_REGISTRATION_TTL_MINUTES} minutes."""
        
    except Exception as e:
        logger.error(f"GST PDF processing error: {str(e)}")
        return f"""❌ *PDF Processing Failed*

An error occurred while processing your GST certificate PDF.

Please try:
• Upload an image (JPG/PNG) instead
• Register manually at https://oemlinker.com/register
• Type *register YOUR_GST_NUMBER*

Contact support@oemlinker.com for assistance."""


async def process_machine_photo_upload(image_url: str, sender: str, vendor: dict, caption: str = "") -> str:
    """
    Process machine photo uploaded via WhatsApp by a registered vendor.
    Uses AI Vision to identify the machine and automatically add it to vendor's profile.
    
    Args:
        image_url: URL of the uploaded image from Gupshup
        sender: WhatsApp sender phone number
        vendor: Vendor document from database
        caption: Optional caption sent with the image
        
    Returns:
        Response message string
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    import base64
    
    try:
        # Send processing message
        if whatsapp_service.is_configured():
            await whatsapp_service.send_text_message(
                sender,
                "📷 *Machine Photo Received*\n\n⏳ Analyzing machine details..."
            )
        
        # Download image from Gupshup URL
        logger.info(f"Downloading machine photo from: {image_url[:50]}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=30.0)
            if response.status_code != 200:
                logger.error(f"Failed to download machine image: HTTP {response.status_code}")
                return """⚠️ *Image Download Failed*

Could not download the image. Please try again.

You can also add machines manually at https://oemlinker.com/vendor/machines"""
            
            image_data = response.content
        
        # Convert to base64 for AI analysis
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Check if we have the API key
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.error("EMERGENT_LLM_KEY not configured for machine identification")
            return """⚠️ *Service Unavailable*

AI service is not configured. Please add machines manually at https://oemlinker.com/vendor/machines"""
        
        # Get machine categories for AI context
        machine_categories_list = []
        for cat, data in MACHINE_CATEGORIES.items():
            types = data.get("types", [])
            machine_categories_list.append(f"- {cat}: {', '.join(types[:5])}")
        categories_context = "\n".join(machine_categories_list)
        
        # Use AI Vision to identify the machine
        chat = LlmChat(
            api_key=api_key,
            session_id=f"machine_id_{sender}_{uuid.uuid4().hex[:8]}",
            system_message=f"""You are an expert at identifying industrial manufacturing machines and equipment.

Your task is to analyze the uploaded machine photo and identify:
1. Machine Name (brand and model if visible, e.g., "Mazak Quick Turn 250")
2. Machine Type (specific type, e.g., "CNC Turning Center", "Vertical Machining Center")
3. Machine Category (one of the categories below)

Available Machine Categories and Types:
{categories_context}

RESPOND IN THIS EXACT JSON FORMAT ONLY:
{{
    "name": "Brand Model" or "Unknown Machine" if not identifiable,
    "machine_type": "specific machine type",
    "machine_category": "category from the list above",
    "brand": "manufacturer brand" or "Unknown",
    "model": "model number" or "Unknown",
    "confidence": "high", "medium", or "low",
    "description": "brief description of what you see"
}}

If the image is not a machine or equipment, respond with:
{{
    "error": "not_a_machine",
    "description": "what the image shows instead"
}}

Important:
- Be specific about machine type
- Use the exact category names from the list
- If you can't identify the brand/model, still identify the type and category
- Confidence should reflect how certain you are about the identification"""
        )
        
        # Create message with image and optional caption context
        prompt_text = "Please identify this manufacturing machine/equipment."
        if caption:
            prompt_text += f"\n\nUser provided caption: {caption}"
        
        user_message = UserMessage(
            text=prompt_text,
            file_contents=[ImageContent(image_base64=image_base64)]
        )
        
        # Get AI response
        ai_response = await chat.send_message(user_message)
        logger.info(f"AI machine identification result for {sender[:6]}***: {ai_response[:100]}...")
        
        # Parse AI response
        try:
            # Clean the response - remove markdown code blocks if present
            clean_response = ai_response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            clean_response = clean_response.strip()
            
            import json
            machine_info = json.loads(clean_response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {str(e)}")
            return f"""⚠️ *Identification Failed*

Could not identify the machine from the image.

Please try:
• Take a clearer photo showing the machine fully
• Include the nameplate/brand in the photo
• Add a caption describing the machine

Or add manually at https://oemlinker.com/vendor/machines"""
        
        # Check if it's an error response
        if "error" in machine_info:
            error_desc = machine_info.get("description", "Unknown")
            return f"""⚠️ *Not a Machine*

This doesn't appear to be a manufacturing machine.

Detected: {error_desc}

Please upload a photo of your:
🏭 CNC machines
🔧 Lathes, mills, grinders
⚙️ Manufacturing equipment

Or add manually at https://oemlinker.com/vendor/machines"""
        
        # Extract machine details
        machine_name = machine_info.get("name", "Unknown Machine")
        machine_type = machine_info.get("machine_type", "")
        machine_category = machine_info.get("machine_category", "")
        brand = machine_info.get("brand", "Unknown")
        model = machine_info.get("model", "Unknown")
        confidence = machine_info.get("confidence", "medium")
        description = machine_info.get("description", "")
        
        # Check if machine name is unknown/generic
        is_name_unknown = (
            not machine_name or 
            machine_name.lower() in ["unknown machine", "unknown", "machine", "unknown unknown"] or
            machine_name.strip() == "" or
            (brand.lower() == "unknown" and model.lower() == "unknown")
        )
        
        # Validate machine type against known categories
        valid_type = False
        for cat, data in MACHINE_CATEGORIES.items():
            if machine_type in data.get("types", []):
                valid_type = True
                if not machine_category:
                    machine_category = cat
                break
        
        if not valid_type and machine_type:
            # Try to find closest category based on type name
            machine_type_lower = machine_type.lower()
            for cat, data in MACHINE_CATEGORIES.items():
                for t in data.get("types", []):
                    if t.lower() in machine_type_lower or machine_type_lower in t.lower():
                        machine_category = cat
                        machine_type = t
                        valid_type = True
                        break
                if valid_type:
                    break
        
        if not machine_category:
            machine_category = "Milling/VMC"  # Default category
        if not machine_type:
            machine_type = "CNC Machine"  # Default type
        
        # Upload image to AWS S3 (required - no local fallback)
        from app.services.s3_storage_service import upload_file
        
        try:
            result = upload_file(
                data=image_data,
                filename=f"machine_{uuid.uuid4().hex[:8]}.jpg",
                folder=f"machines/{vendor['vendor_id']}",
                content_type="image/jpeg"
            )
            image_url_stored = result["url"]  # Use S3 public URL
            logger.info(f"Machine image uploaded to S3: {image_url_stored}")
        except Exception as e:
            logger.error(f"S3 upload failed for WhatsApp machine image: {e}")
            return f"""❌ *Upload Failed*

Sorry, we couldn't save your machine image. Please try again later.

Error: Storage service unavailable

If this problem persists, please contact support."""
        
        # Get vendor's language for localized instructions
        lang_info = get_vendor_language(vendor)
        lang_code = lang_info.get("code", "hi")
        lang_name = lang_info.get("lang", "Hindi")
        
        # If machine name is unknown, ask for it first
        if is_name_unknown:
            logger.info(f"Machine name not identified for sender '{sender}', asking for name")
            
            # Store pending machine with waiting_for_name step
            pending_machines[sender] = {
                "machine_info": {
                    "name": "",  # Will be filled by user
                    "machine_category": machine_category,
                    "machine_type": machine_type,
                    "brand": brand if brand.lower() != "unknown" else "",
                    "model": model if model.lower() != "unknown" else "",
                    "confidence": confidence,
                    "description": description
                },
                "image_url": image_url_stored,
                "vendor_id": vendor["vendor_id"],
                "step": "waiting_for_name",
                "field_index": 0,
                "dimensions": {},
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=PENDING_MACHINE_TTL_MINUTES)
            }
            
            # Bilingual prompt for machine name
            name_prompts = {
                "hi": "_मशीन का नाम बताएं (जैसे: Mazak CNC Lathe)_",
                "mr": "_मशीनचे नाव सांगा (उदा: Mazak CNC Lathe)_",
                "gu": "_મશીનનું નામ જણાવો (દા.ત.: Mazak CNC Lathe)_",
                "ta": "_இயந்திரத்தின் பெயரைக் கூறுங்கள் (எ.கா.: Mazak CNC Lathe)_",
                "te": "_మెషిన్ పేరు చెప్పండి (ఉదా: Mazak CNC Lathe)_",
                "kn": "_ಯಂತ್ರದ ಹೆಸರು ಹೇಳಿ (ಉದಾ: Mazak CNC Lathe)_",
                "bn": "_মেশিনের নাম বলুন (যেমন: Mazak CNC Lathe)_",
                "pa": "_ਮਸ਼ੀਨ ਦਾ ਨਾਮ ਦੱਸੋ (ਜਿਵੇਂ: Mazak CNC Lathe)_"
            }
            
            regional_prompt = name_prompts.get(lang_code, name_prompts["hi"])
            
            return f"""📷 *Machine Photo Received!*

⚠️ Could not identify the machine name automatically.

📝 *Please enter the machine name:*
{regional_prompt}

Example: _Mazak Quick Turn 200_ or _Haas VF-2_

━━━━━━━━━━━━━━━━━━━━━━
📂 Detected Category: {machine_category}
📋 Detected Type: {machine_type}

Type *cancel* to abort."""
        
        # Machine name is known - proceed with dimension collection
        # Get dimension fields for this machine category using fuzzy matching
        dim_config = get_dimension_config_for_category(machine_category)
        fields_list = dim_config["fields"]
        first_field_info = fields_list[0]
        first_field_key = first_field_info["key"]
        first_prompt_en = first_field_info["prompt"]
        # Get bilingual prompt based on vendor's state
        first_prompt = get_bilingual_prompt(first_field_key, first_prompt_en, vendor)
        
        # Use the identified name or construct from brand/model
        final_machine_name = machine_name if machine_name != "Unknown Machine" else f"{brand} {model}".strip()
        
        # Store pending machine for dimension collection
        logger.info(f"Setting pending_machines for sender: '{sender}', category: '{machine_category}'")
        pending_machines[sender] = {
            "machine_info": {
                "name": final_machine_name,
                "machine_category": machine_category,
                "machine_type": machine_type,
                "brand": brand,
                "model": model,
                "confidence": confidence,
                "description": description
            },
            "image_url": image_url_stored,
            "vendor_id": vendor["vendor_id"],
            "step": first_field_key,
            "field_index": 0,
            "dimensions": {},
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=PENDING_MACHINE_TTL_MINUTES)
        }
        
        # Prepare confidence indicator
        confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🟠"}.get(confidence, "🟡")
        
        # Build a preview of dimension fields that will be asked
        total_fields = len(fields_list)
        fields_preview = ", ".join([f["label"].replace(" (mm)", "").replace(" (kg)", "").replace(" (°)", "").replace(" (μm)", "").replace(" (kW)", "").replace(" (A)", "").replace(" (°C)", "").replace(" (ton)", "") for f in fields_list[:3]])
        if total_fields > 3:
            fields_preview += f" +{total_fields - 3} more"
        
        # Get bilingual messages
        machine_identified_regional = get_bilingual_message("machine_identified", vendor)
        add_dimensions_regional = get_bilingual_message("add_dimensions", vendor)
        
        logger.info(f"Machine identified via WhatsApp, starting dimension flow: {final_machine_name} for vendor {vendor['vendor_id']} (lang: {lang_name})")
        
        return f"""✅ *Machine Identified!*{machine_identified_regional}

{confidence_emoji} AI Identification ({confidence} confidence)

🏭 *{final_machine_name}*
📋 Type: {machine_type}
📂 Category: {machine_category}
🔧 Brand: {brand}
📝 Model: {model}

━━━━━━━━━━━━━━━━━━━━━━
📏 *Now let's add dimensions:*{add_dimensions_regional}
_{fields_preview}_

*Step 1/{total_fields}:*
{first_prompt}

📷 _Or send a photo of the machine *nameplate/spec sheet* to auto-fill dimensions!_

Type *skip* to skip dimensions and save machine as-is."""
        
    except Exception as e:
        logger.error(f"Machine photo processing error: {str(e)}")
        return f"""❌ *Processing Failed*

An error occurred while processing your machine photo.

Please try again or add machines manually at https://oemlinker.com/vendor/machines

Contact support@oemlinker.com for assistance."""


async def save_pending_machine(sender: str, vendor: dict) -> str:
    """Save the pending machine with collected dimensions"""
    try:
        if sender not in pending_machines:
            return "⚠️ No pending machine to save."
        
        pending = pending_machines[sender]
        machine_info = pending["machine_info"]
        dimensions = pending.get("dimensions", {})
        
        # Create machine entry with all possible dimension fields
        machine_id = f"machine_{uuid.uuid4().hex[:12]}"
        machine_doc = {
            "machine_id": machine_id,
            "vendor_id": vendor["vendor_id"],
            "name": machine_info["name"],
            "machine_category": machine_info["machine_category"],
            "machine_type": machine_info["machine_type"],
            "brand": machine_info["brand"],
            "model": machine_info["model"],
            "images": [pending["image_url"]],
            # Standard dimension fields
            "max_x": dimensions.get("max_x"),
            "max_y": dimensions.get("max_y"),
            "max_z": dimensions.get("max_z"),
            "max_diameter": dimensions.get("max_diameter"),
            "max_length": dimensions.get("max_length"),
            "max_swing": dimensions.get("max_swing"),
            # Boring/Drilling specific
            "bore_diameter": dimensions.get("bore_diameter"),
            "spindle_bore": dimensions.get("spindle_bore"),
            "spindle_travel": dimensions.get("spindle_travel"),
            "arm_length": dimensions.get("arm_length"),
            "max_depth": dimensions.get("max_depth"),
            # VTL/Table specific
            "table_diameter": dimensions.get("table_diameter"),
            "table_size_x": dimensions.get("table_size_x"),
            "table_size_y": dimensions.get("table_size_y"),
            "pallet_size": dimensions.get("pallet_size"),
            "max_weight": dimensions.get("max_weight"),
            # Shaping specific
            "max_stroke": dimensions.get("max_stroke"),
            "stroke": dimensions.get("stroke"),
            # Gear specific
            "max_module": dimensions.get("max_module"),
            "min_teeth": dimensions.get("min_teeth"),
            # 5-Axis specific
            "a_axis_range": dimensions.get("a_axis_range"),
            "c_axis_range": dimensions.get("c_axis_range"),
            # Sheet Metal/Press specific
            "tonnage": dimensions.get("tonnage"),
            "max_thickness": dimensions.get("max_thickness"),
            # Laser specific
            "laser_power": dimensions.get("laser_power"),
            # Welding specific
            "amperage": dimensions.get("amperage"),
            # Heat Treatment specific
            "max_temp": dimensions.get("max_temp"),
            # Inspection specific
            "accuracy": dimensions.get("accuracy"),
            # Additive specific
            "layer_thickness": dimensions.get("layer_thickness"),
            # EDM specific
            "max_taper_angle": dimensions.get("max_taper_angle"),
            # Tolerance (common across most machines)
            "tolerance": dimensions.get("tolerance", 0.01),
            "tolerance_capability": dimensions.get("tolerance", 0.01),
            # Other fields
            "materials_supported": [],
            "monthly_capacity_hours": 160,
            "is_active": True,
            "availability_status": "available",
            "ai_identified": True,
            "ai_confidence": machine_info.get("confidence", "medium"),
            "ai_description": machine_info.get("description", ""),
            "source": "whatsapp",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Remove None values to keep document clean
        machine_doc = {k: v for k, v in machine_doc.items() if v is not None}
        
        await db.machines.insert_one(machine_doc)
        logger.info(f"Machine saved via WhatsApp: {machine_id} for vendor {vendor['vendor_id']}")
        
        # Get machine count
        machine_count = await db.machines.count_documents({"vendor_id": vendor["vendor_id"]})
        
        # Build dimensions summary using the category-specific fields
        dim_config = get_dimension_config_for_category(machine_info["machine_category"])
        dim_summary = []
        for field in dim_config["fields"]:
            field_key = field["key"]
            if dimensions.get(field_key):
                label = field["label"].replace(" (mm)", "").replace(" (kg)", "").replace(" (°)", "").replace(" (μm)", "").replace(" (kW)", "").replace(" (A)", "").replace(" (°C)", "").replace(" (ton)", "")
                value = dimensions[field_key]
                dim_summary.append(f"{label}: {value}")
        
        dim_text = ", ".join(dim_summary) if dim_summary else "No dimensions added"
        
        # Get bilingual message
        machine_saved_regional = get_bilingual_message("machine_saved", vendor)
        
        return f"""✅ *Machine Saved Successfully!*{machine_saved_regional}

🏭 *{machine_info['name']}*
📋 Type: {machine_info['machine_type']}
📂 Category: {machine_info['machine_category']}
📏 Dimensions: {dim_text}

📸 Photo saved to your profile

You now have *{machine_count} machines* in your profile.

━━━━━━━━━━━━━━━━━━━━━━
📷 Send more machine photos to add them
✏️ Edit details at https://oemlinker.com/vendor/machines

Type *machines* to see all your machines"""
        
    except Exception as e:
        logger.error(f"Error saving pending machine: {str(e)}")
        return "❌ Error saving machine. Please try again."


async def process_nameplate_image(image_url: str, sender: str, vendor: dict) -> str:
    """
    Process nameplate/spec sheet image to extract machine dimensions.
    Uses AI Vision to read specifications from the image.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    import base64
    
    try:
        if sender not in pending_machines:
            return "⚠️ No pending machine. Send a machine photo first."
        
        pending = pending_machines[sender]
        machine_category = pending["machine_info"]["machine_category"]
        
        # Download image
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=30.0)
            if response.status_code != 200:
                return "⚠️ Could not download image. Please try again."
            image_data = response.content
        
        # Convert to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get relevant dimension fields for this machine type using new structure
        dim_config = get_dimension_config_for_category(machine_category)
        fields_list = dim_config["fields"]
        fields_to_extract = [f["key"] for f in fields_list]
        fields_labels = {f["key"]: f["label"] for f in fields_list}
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return "⚠️ AI service not configured."
        
        # Build dynamic JSON schema based on category fields
        json_fields = "\n    ".join([f'"{f["key"]}": number or null,' for f in fields_list])
        
        # Use AI to extract specifications
        chat = LlmChat(
            api_key=api_key,
            session_id=f"nameplate_{sender}_{uuid.uuid4().hex[:8]}",
            system_message=f"""You are an expert at reading machine nameplates and specification sheets.

Extract the following specifications from the image:
{', '.join([f'{f["key"]} ({f["label"]})' for f in fields_list])}

RESPOND IN THIS EXACT JSON FORMAT:
{{
    {json_fields}
}}

Notes:
- Convert all values to the appropriate unit (mm for dimensions, degrees for angles, etc.)
- Use null if value not found
- Look for: travel, stroke, capacity, diameter, length, tolerance, accuracy, power, amperage
- Common labels: X-axis, Y-axis, Z-axis, spindle, chuck, bed, table, capacity"""
        )
        
        user_message = UserMessage(
            text="Extract machine specifications from this nameplate/spec sheet.",
            file_contents=[ImageContent(image_base64=image_base64)]
        )
        
        ai_response = await chat.send_message(user_message)
        
        # Parse response
        try:
            clean_response = ai_response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            clean_response = clean_response.strip()
            
            import json
            specs = json.loads(clean_response)
        except:
            return """⚠️ *Could not read specifications*

Please enter dimensions manually or type *skip* to save without dimensions."""
        
        # Update pending machine with extracted dimensions
        extracted = []
        for field_key in fields_to_extract:
            if specs.get(field_key) is not None:
                pending["dimensions"][field_key] = specs[field_key]
                label = fields_labels.get(field_key, field_key.replace('_', ' ').title())
                extracted.append(f"{label}: {specs[field_key]}")
        
        if not extracted:
            return """⚠️ *No specifications found in image*

Please enter dimensions manually or type *skip* to save without dimensions."""
        
        # Save machine with extracted dimensions
        response_message = await save_pending_machine(sender, vendor)
        if sender in pending_machines:
            del pending_machines[sender]
        
        return f"""📋 *Specifications Extracted!*

{chr(10).join(['✅ ' + e for e in extracted])}

{response_message}"""
        
    except Exception as e:
        logger.error(f"Nameplate processing error: {str(e)}")
        return """❌ *Processing Failed*

Please enter dimensions manually or type *skip* to save without dimensions."""


async def process_whatsapp_registration(sender: str, gst_number: str) -> str:
    """Process vendor registration via WhatsApp using GST number"""
    import secrets
    import random
    
    try:
        # Check if GST is already registered
        existing_vendor = await db.vendors.find_one({"gstin": gst_number}, {"_id": 0})
        if existing_vendor:
            return f"""⚠️ *GST Already Registered*

This GST number is already linked to a vendor account.

If this is your account, please:
1. Login at https://oemlinker.com/login
2. Update your phone number in profile settings

Or contact support@oemlinker.com for help."""

        # Check if phone number is already registered
        existing_user = await db.users.find_one({"phone": sender}, {"_id": 0})
        if existing_user:
            return f"""⚠️ *Phone Already Registered*

This phone number is already linked to an account.

Please login at https://oemlinker.com/login
Or contact support@oemlinker.com for help."""

        # Validate GST using external API
        GSTIN_API_KEY = os.environ.get("GSTIN_API_KEY", "")
        gst_data = None
        
        if GSTIN_API_KEY:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://sheet.gstincheck.co.in/check/{GSTIN_API_KEY}/{gst_number}",
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("flag"):
                            gst_data = result.get("data", {})
            except Exception as e:
                logger.warning(f"GST validation API error: {str(e)}")
        
        if not gst_data:
            return f"""⚠️ *GST Validation Failed*

Could not validate GST number: {gst_number}

Please check if:
1. GST number is correct
2. GST is active and valid

You can also register manually at https://oemlinker.com/register"""

        # Extract company details from GST data
        company_name = gst_data.get("tradeNam") or gst_data.get("lgnm", "Unknown Company")
        legal_name = gst_data.get("lgnm", "")
        trade_name = gst_data.get("tradeNam", "")
        gst_status = gst_data.get("sts", "")
        taxpayer_type = gst_data.get("dty", "")
        constitution = gst_data.get("ctb", "")
        registration_date = gst_data.get("rgdt", "")
        
        # Extract address details
        pradr = gst_data.get("pradr", {})
        address_parts = []
        if pradr.get("adr"):
            address_parts.append(pradr["adr"])
        
        # More detailed address parsing
        addr_obj = pradr.get("addr", {})
        building = addr_obj.get("bnm", "") or addr_obj.get("bno", "")
        street = addr_obj.get("st", "")
        locality = addr_obj.get("loc", "") or addr_obj.get("dst", "")
        city = pradr.get("loc", "") or addr_obj.get("dst", "")
        state = pradr.get("stcd", "")
        pincode = pradr.get("pncd", "") or addr_obj.get("pncd", "")
        
        # Build full address if not available from adr field
        if not address_parts:
            full_address_parts = [building, street, locality]
            address_parts = [", ".join(filter(None, full_address_parts))]
        
        # Use 10-digit phone number as login ID (remove country code 91)
        phone_normalized = sender.replace("+", "").replace(" ", "").replace("-", "")
        # Extract last 10 digits (remove 91 prefix if present)
        if phone_normalized.startswith("91") and len(phone_normalized) > 10:
            phone_login = phone_normalized[-10:]
        else:
            phone_login = phone_normalized[-10:] if len(phone_normalized) >= 10 else phone_normalized
        
        # Generate 6-digit numeric password
        numeric_password = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Create user account
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        password_hash = pwd_context.hash(numeric_password)
        
        user_doc = {
            "user_id": user_id,
            "email": phone_login,  # Phone number as login ID
            "password_hash": password_hash,
            "name": company_name,
            "role": UserRole.VENDOR,
            "is_verified": True,  # Auto-verify for WhatsApp registration
            "phone": sender,
            "phone_login": True,  # Flag to indicate phone-based login
            "created_at": datetime.now(timezone.utc).isoformat(),
            "registered_via": "whatsapp"
        }
        
        await db.users.insert_one(user_doc)
        
        # Create vendor profile with all GST data
        vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
        vendor_doc = {
            "vendor_id": vendor_id,
            "user_id": user_id,
            "company_name": company_name,
            "legal_name": legal_name,
            "trade_name": trade_name,
            "gstin": gst_number,
            "gst_verified": True,
            "gst_status": gst_status,
            "gst_data": gst_data,  # Store raw GST data for reference
            "taxpayer_type": taxpayer_type,
            "constitution": constitution,
            "gst_registration_date": registration_date,
            "address": ", ".join(filter(None, address_parts)),
            "city": city,
            "state": state,
            "pincode": pincode,
            "country": "India",
            "phone": sender,
            "is_approved": False,  # Needs admin approval
            "rating": 0,
            "total_jobs": 0,
            "machines": [],
            "certifications": [],
            "industries": [],
            "materials_handled": [],
            "past_experiences": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "registered_via": "whatsapp"
        }
        
        await db.vendors.insert_one(vendor_doc)
        
        # Send admin notification
        asyncio.create_task(send_admin_notification("new_vendor_registration", {
            "vendor_id": vendor_id,
            "company_name": company_name,
            "gstin": gst_number,
            "phone": sender,
            "registered_via": "WhatsApp"
        }))
        
        logger.info(f"New vendor registered via WhatsApp: {company_name} (GST: {gst_number}, Phone: {phone_login})")
        
        # Generate magic link for instant login
        magic_token = secrets.token_urlsafe(32)
        magic_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry for new registration
        
        await db.magic_link_tokens.insert_one({
            "token": magic_token,
            "user_id": user_id,
            "phone": sender,
            "expires_at": magic_expires_at.isoformat(),
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "type": "registration"
        })
        
        # Build magic login URL
        BASE_URL = "https://oemlinker.com"
        magic_login_url = f"{BASE_URL}/magic-login?token={magic_token}"
        
        # Get bilingual messages
        new_vendor = {"state": state}
        success_regional = get_bilingual_message("registration_success", new_vendor)
        welcome_regional = get_bilingual_message("welcome", new_vendor)
        
        return f"""🎉 *Registration Successful!*{success_regional}

Welcome to *OEMLinker*, {company_name}!{welcome_regional}

✅ *Account Created*
🏢 Company: {company_name}
📋 GST: {gst_number}
📍 Location: {city}, {state}

🔗 *Quick Login (Tap to open):*
{magic_login_url}

_Link valid for 24 hours_

🔐 *Manual Login:*
📱 Login ID: *{phone_login}*
🔑 Password: *{numeric_password}*

💡 *Next Steps:*
• Add your machines to receive RFQ matches
• Type *email* to add notifications
• Type *help* for commands

📷 *Quick Tip:* Send machine photos to add them!"""

    except Exception as e:
        logger.error(f"WhatsApp registration error: {str(e)}")
        return f"""❌ *Registration Failed*

An error occurred during registration. Please try again or register manually at https://oemlinker.com/register

Error: {str(e)[:100]}

Contact support@oemlinker.com for assistance."""



async def process_whatsapp_command(
    text: str, 
    sender: str, 
    vendor: Optional[dict], 
    user: Optional[dict]
) -> str:
    """Process WhatsApp commands and return response"""
    
    # Normalize text for fuzzy matching (voice transcription can be inaccurate)
    text_normalized = text.lower().strip()
    
    # Helper function for fuzzy command matching - works with sentences
    def matches_command(input_text: str, commands: list) -> bool:
        input_text = input_text.lower().strip()
        input_no_spaces = input_text.replace(" ", "")
        input_words = set(input_text.split())
        
        for cmd in commands:
            cmd_lower = cmd.lower()
            
            # Exact match (highest priority)
            if input_text == cmd_lower:
                return True
            
            # For short commands (<=3 chars like "hi"), require exact word match
            if len(cmd_lower) <= 3:
                if cmd_lower in input_words:
                    return True
            else:
                # Direct substring match for longer commands
                if cmd_lower in input_text:
                    return True
                # Reverse check (short input matches longer command)
                if input_text in cmd_lower:
                    return True
            
            # No-space match for voice errors like "myorders"
            if len(cmd_lower) > 3 and cmd_lower.replace(" ", "") in input_no_spaces:
                return True
            
            # Word-based match - check if command words appear in the sentence
            cmd_words = cmd_lower.split()
            if len(cmd_words) > 1:
                # For multi-word commands, check if all words appear
                if all(word in input_words for word in cmd_words):
                    return True
        return False
    
    # Also check for action verbs + command patterns (including Indian languages)
    def extract_intent(input_text: str) -> str:
        """Extract intent from natural language sentences - supports Indian languages"""
        input_text = input_text.lower()
        
        # Patterns for registration
        register_keywords = ["register", "signup", "sign up", "join", "enroll", "new vendor", 
                            "रजिस्टर", "पंजीकरण", "जुड़ें", "নিবন্ধন"]
        if any(word in input_text for word in register_keywords):
            return "register"
        
        # Patterns for RFQs (English + Hindi keywords)
        rfq_keywords = ["rfq", "rfqs", "job", "jobs", "opportunit", "request", "enquir", "inquir", "work", "kaam", "kam", 
                        "काम", "नौकरी", "अवसर", "आरएफक्यू", "कोटेशन", "রিক्वেস্ট"]
        if any(word in input_text for word in rfq_keywords):
            return "rfqs"
        
        # Patterns for orders (English + Hindi keywords)
        order_keywords = ["order", "odor", "ऑर्डर", "आर्डर", "অর্ডার", "ಆರ್ಡರ್"]
        if any(word in input_text for word in order_keywords):
            return "orders"
        
        # Patterns for quotes (English + Hindi keywords)
        quote_keywords = ["quote", "quot", "bid", "कोट", "बोली", "কোট", "மேற்கோள்"]
        if any(word in input_text for word in quote_keywords):
            return "quotes"
        
        # Patterns for profile (English + Hindi keywords)
        profile_keywords = ["profile", "profil", "account", "प्रोफाइल", "खाता", "প্রোফাইল"]
        if any(word in input_text for word in profile_keywords):
            return "profile"
        
        # Patterns for help (English + Hindi keywords)
        help_keywords = ["help", "command", "what can", "मदद", "सहायता", "সাহায্য", "உதவி"]
        if any(word in input_text for word in help_keywords):
            return "help"
        
        return ""
    
    # First try to extract intent from natural language
    intent = extract_intent(text_normalized)
    
    # ===== INDIAN LANGUAGE SUPPORT =====
    # Hindi variants (including common voice transcription variations)
    hindi_rfq = ["आरएफक्यू", "काम", "नौकरी", "अवसर", "काम दिखाओ", "आर्डर दिखाओ", "कोटेशन", "रिक्वेस्ट",
                 "kaam", "naukri", "avsar", "kaam dikhao", "order dikhao"]
    hindi_orders = ["मेरे ऑर्डर", "ऑर्डर", "आर्डर", "मेरा आर्डर", "ऑर्डर दिखाओ", "आर्डर दिखाओ",
                    "mere order", "mera order", "order dikhao"]
    hindi_quotes = ["मेरे कोट्स", "कोट्स", "मेरा कोट", "बोली", "मेरी बोली", "कोटेशन",
                    "mere quotes", "mera quote", "meri boli", "quotation"]
    hindi_profile = ["प्रोफाइल", "मेरी प्रोफाइल", "अकाउंट", "खाता", "मेरा खाता",
                     "meri profile", "mera account", "mera khata"]
    hindi_help = ["मदद", "सहायता", "हेल्प", "मेन्यू", "शुरू",
                  "madad", "sahayata", "help karo", "menu dikhao", "shuru"]
    hindi_machines = ["मशीन", "मेरी मशीन", "मशीनें", "मशीन दिखाओ", "उपकरण",
                      "machine", "meri machine", "machines dikhao", "upkaran"]
    hindi_availability = ["उपलब्धता", "बिजी", "फ्री", "खाली", "व्यस्त", "मशीन खाली", "मशीन बिजी",
                          "availability", "busy", "free", "khali", "vyast", "machine khali", "machine busy",
                          "available karo", "busy karo", "maintenance", "offline"]
    
    # Tamil variants (including romanized versions)
    tamil_rfq = ["வேலை", "வாய்ப்பு", "கோரிக்கை", "velai", "vaippu"]
    tamil_orders = ["என் ஆர்டர்", "ஆர்டர்கள்", "ஆர்டர்", "en order", "orders"]
    tamil_quotes = ["என் மேற்கோள்", "மேற்கோள்கள்", "en quote", "quotes"]
    tamil_profile = ["சுயவிவரம்", "என் சுயவிவரம்", "profile", "en profile"]
    tamil_help = ["உதவி", "மெனு", "உதவி செய்", "uthavi", "menu"]
    tamil_machines = ["இயந்திரம்", "இயந்திரங்கள்", "என் இயந்திரங்கள்", "iyanthiram", "machines"]
    tamil_availability = ["கிடைக்கும்", "பிசி", "ஃப்ரீ", "kidaikkum", "busy", "free"]
    
    # Telugu variants (including romanized versions)
    telugu_rfq = ["పని", "అవకాశం", "అభ్యర్థన", "pani", "avakasam"]
    telugu_orders = ["నా ఆర్డర్లు", "ఆర్డర్లు", "naa orders", "orders"]
    telugu_quotes = ["నా కోట్స్", "కోట్స్", "naa quotes", "quotes"]
    telugu_profile = ["ప్రొఫైల్", "నా ప్రొఫైల్", "naa profile", "profile"]
    telugu_help = ["సహాయం", "మెను", "sahayam", "menu"]
    telugu_machines = ["యంత్రాలు", "నా యంత్రాలు", "machines", "naa machines"]
    telugu_availability = ["అందుబాటులో", "బిజీ", "ఫ్రీ", "andubatulo", "busy", "free"]
    
    # Marathi variants (including romanized versions)
    marathi_rfq = ["काम", "संधी", "विनंती", "kaam", "sandhi", "vinanti"]
    marathi_orders = ["माझे ऑर्डर", "ऑर्डर", "majhe order", "order"]
    marathi_quotes = ["माझे कोट्स", "कोट्स", "majhe quotes", "quotes"]
    marathi_profile = ["प्रोफाइल", "माझी प्रोफाइल", "majhi profile", "profile"]
    marathi_help = ["मदत", "मेनू", "madat", "menu"]
    marathi_machines = ["मशीन", "माझ्या मशीन्स", "मशीन्स", "majhya machines", "machines"]
    marathi_availability = ["उपलब्ध", "बिझी", "फ्री", "uplabdha", "busy", "free"]
    
    # Bengali variants (including romanized versions)
    bengali_rfq = ["কাজ", "সুযোগ", "অনুরোধ", "kaaj", "sujog", "anurodh"]
    bengali_orders = ["আমার অর্ডার", "অর্ডার", "amar order", "order"]
    bengali_quotes = ["আমার কোট", "কোট", "amar quote", "quote"]
    bengali_profile = ["প্রোফাইল", "আমার প্রোফাইল", "amar profile", "profile"]
    bengali_help = ["সাহায্য", "মেনু", "sahajyo", "menu"]
    bengali_machines = ["যন্ত্র", "আমার যন্ত্র", "jantra", "amar machines", "machines"]
    bengali_availability = ["উপলব্ধ", "বিজি", "ফ্রি", "upolabdho", "busy", "free"]
    
    # Gujarati variants (including romanized versions)
    gujarati_rfq = ["કામ", "તક", "વિનંતી", "kaam", "tak", "vinanti"]
    gujarati_orders = ["મારા ઓર્ડર", "ઓર્ડર", "mara order", "order"]
    gujarati_quotes = ["મારા કોટ્સ", "કોટ્સ", "mara quotes", "quotes"]
    gujarati_profile = ["પ્રોફાઇલ", "મારી પ્રોફાઇલ", "mari profile", "profile"]
    gujarati_help = ["મદદ", "મેનુ", "madad", "menu"]
    gujarati_machines = ["મશીન", "મારી મશીનો", "machine", "mari machines"]
    gujarati_availability = ["ઉપલબ્ધ", "બિઝી", "ફ્રી", "uplabdh", "busy", "free"]
    
    # Kannada variants (including romanized versions)
    kannada_rfq = ["ಕೆಲಸ", "ಅವಕಾಶ", "kelasa", "avakasha"]
    kannada_orders = ["ನನ್ನ ಆರ್ಡರ್", "ಆರ್ಡರ್", "nanna order", "order"]
    kannada_quotes = ["ನನ್ನ ಕೋಟ್ಸ್", "ಕೋಟ್ಸ್", "nanna quotes", "quotes"]
    kannada_profile = ["ಪ್ರೊಫೈಲ್", "nanna profile", "profile"]
    kannada_help = ["ಸಹಾಯ", "ಮೆನು", "sahaya", "menu"]
    kannada_machines = ["ಯಂತ್ರ", "ನನ್ನ ಯಂತ್ರಗಳು", "yantra", "nanna machines"]
    kannada_availability = ["ಲಭ್ಯ", "ಬಿಜಿ", "ಫ್ರೀ", "labhya", "busy", "free"]
    
    # Punjabi variants (including romanized versions)
    punjabi_rfq = ["ਕੰਮ", "ਮੌਕਾ", "kamm", "mauka"]
    punjabi_orders = ["ਮੇਰੇ ਆਰਡਰ", "ਆਰਡਰ", "mere order", "order"]
    punjabi_quotes = ["ਮੇਰੇ ਕੋਟਸ", "ਕੋਟਸ", "mere quotes", "quotes"]
    punjabi_profile = ["ਪ੍ਰੋਫਾਈਲ", "meri profile", "profile"]
    punjabi_help = ["ਮਦਦ", "ਮੀਨੂ", "madad", "menu"]
    punjabi_machines = ["ਮਸ਼ੀਨ", "ਮੇਰੀਆਂ ਮਸ਼ੀਨਾਂ", "machine", "meri machines"]
    punjabi_availability = ["ਉਪਲਬਧ", "ਬਿਜ਼ੀ", "ਫ੍ਰੀ", "uplabdh", "busy", "free"]
    
    # Help command - expanded with Indian languages
    help_variants = ["help", "hi", "hello", "menu", "start", "hey", "helo", "assist", "assistance",
                     *hindi_help, *tamil_help, *telugu_help, *marathi_help,
                     *bengali_help, *gujarati_help, *kannada_help, *punjabi_help]
    if intent == "help" or matches_command(text_normalized, help_variants):
        if vendor:
            # Get bilingual welcome message
            welcome_regional = get_bilingual_message("welcome_vendor", vendor)
            help_regional = get_bilingual_message("help", vendor)
            commands_regional = get_bilingual_message("available_commands", vendor)
            
            return f"""👋 Welcome to *OEMLinker*, {vendor.get('company_name', 'Vendor')}!{welcome_regional}

📋 *Available Commands:*{commands_regional}

*rfqs* - View matched RFQs 📎 (drawings shown)
*rfq <id>* - Get RFQ details + drawing PDF
*drawing <id>* - Get drawing for an RFQ
*my quotes* - View your submitted quotes
*my orders* - View your active orders
*machines* - View machines & set availability
*profile* - View your vendor profile
*email* - Add/update your email address
*login* - Get instant login link for web dashboard 🔗
*help* - Show this menu{help_regional}

📷 *Add Machine:* Send a photo of your machine!
🎤 *Voice Search:* Send a voice message to search!

💡 You can also ask questions in natural language!

Example: "Show me urgent RFQs for steel machining" """
        else:
            return """👋 Welcome to *OEMLinker*!

Your phone number is not linked to a vendor account.

📝 *Register via WhatsApp:*

📷 Send a photo of your *GST Certificate*
_We'll automatically extract your details and create your account!_

━━━━━━━━━━━━━━━━━━━━━━
📷 _Just send your GST certificate image to get started!_"""

    # Check for GST-based registration (for non-registered users)
    import re
    gst_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
    gst_match = re.search(gst_pattern, text.upper())
    
    register_variants = ["register", "signup", "sign up", "join", "enroll", "रजिस्टर", "पंजीकरण"]
    is_registration_request = intent == "register" or matches_command(text_normalized, register_variants) or gst_match
    
    if is_registration_request and not vendor:
        # Extract GST number
        if gst_match:
            gst_number = gst_match.group(0)
            return await process_whatsapp_registration(sender, gst_number)
        else:
            # For non-registered users, use Hindi as default
            default_vendor = {"state": ""}
            reg_regional = get_bilingual_message("registration", default_vendor)
            send_gst_regional = get_bilingual_message("send_gst", default_vendor)
            
            return f"""📝 *Vendor Registration*{reg_regional}

📷 Send a photo of your *GST Certificate*{send_gst_regional}
_AI will read and fill your details automatically!_

━━━━━━━━━━━━━━━━━━━━━━
Your account will be created with business details from GSTIN database."""

    # Must be a registered vendor for other commands
    if not vendor:
        default_vendor = {"state": ""}
        send_gst_regional = get_bilingual_message("send_gst", default_vendor)
        
        return f"""⚠️ Your phone is not linked to a vendor account.

📷 *Register Now:*
Send a photo of your *GST Certificate* to register instantly!{send_gst_regional}"""
    
    # Base URL for links
    BASE_URL = "https://oemlinker.com"
    
    # List RFQs command - expanded with Indian languages
    rfq_variants = ["rfqs", "rfq", "jobs", "opportunities", "open rfqs", "show rfqs", "list rfqs", 
                    "our effects", "our fq", "r f q", "requests", "request for quote",
                    "enquiry", "enquiries", "inquiry", "inquiries", "work", "works",
                    "kaam", "kam", "kam dikha", "kaam dikhao", "kaam dikhaao",
                    *hindi_rfq, *tamil_rfq, *telugu_rfq, *marathi_rfq, *bengali_rfq, 
                    *gujarati_rfq, *kannada_rfq, *punjabi_rfq]
    if intent == "rfqs" or matches_command(text_normalized, rfq_variants):
        # Check if user is a registered vendor
        if not vendor:
            return f"""📭 *You're not registered as a vendor yet!*

To view RFQ opportunities, you need to register first.

📸 *How to Register:*
Send a photo of your *GST Certificate* to register instantly!

Or visit: {BASE_URL}/register"""
        
        try:
            # Get matched RFQs for this vendor
            vendor_id = vendor.get("vendor_id")
            logger.info(f"RFQs command: Looking for RFQs matched to vendor_id={vendor_id}")
            
            rfqs = await db.rfqs.find(
                {
                    "status": {"$in": ["submitted", "matching", "quoted"]},
                    "matched_vendors.vendor_id": vendor_id
                },
                {"_id": 0, "rfq_id": 1, "title": 1, "material_type": 1, "quantity": 1, "urgency": 1, "matched_vendors": 1, "drawing_ids": 1, "ai_analysis": 1}
            ).sort("created_at", -1).limit(5).to_list(length=5)
            
            logger.info(f"RFQs command: Found {len(rfqs)} RFQs")
            
            if not rfqs:
                return f"📭 No matching RFQs found at the moment.\n\n🔗 View all RFQs: {BASE_URL}/vendor/dashboard"
            
            response = "📋 *Your Matched RFQs:*\n\n"
            for rfq in rfqs:
                rfq_id = rfq.get('rfq_id', '')
                short_id = rfq_id.replace("rfq_", "")[:8] if rfq_id else ""
                urgency_emoji = {"urgent": "🔴", "high": "🟠", "normal": "🟢", "low": "🔵"}.get(rfq.get("urgency", "normal"), "🟢")
                
                # Find match score for this vendor
                match_score = 0
                matched_vendors = rfq.get("matched_vendors") or []
                for m in matched_vendors:
                    if m and m.get("vendor_id") == vendor_id:
                        # Score is stored as "suitability_score" in database
                        match_score = m.get("suitability_score", m.get("match_score", 0))
                        break
                
                # Check for drawings
                drawing_ids = rfq.get("drawing_ids") or []
                has_drawings = len(drawing_ids) > 0
                drawing_indicator = "📎" if has_drawings else ""
                
                # Get recommended processes from AI analysis
                ai_analysis = rfq.get("ai_analysis") or {}
                processes = (ai_analysis.get("recommended_processes") or [])[:2]
                process_str = f"🔧 {', '.join(processes)}" if processes else ""
                
                # Generate magic link for instant access to RFQ
                magic_result = await generate_magic_link_for_vendor(sender, f"/vendor/rfq/{rfq_id}")
                if magic_result.get("success"):
                    rfq_link = f"{BASE_URL}/magic-login?token={magic_result['token']}"
                else:
                    rfq_link = f"{BASE_URL}/vendor/rfq/{rfq_id}"
                
                response += f"{urgency_emoji} *{rfq.get('title', 'Untitled')[:35]}* {drawing_indicator}\n"
                response += f"   Material: {rfq.get('material_type', 'N/A')} | Qty: {rfq.get('quantity', 'N/A')}\n"
                response += f"   Match Score: {match_score}%"
                if process_str:
                    response += f" | {process_str}"
                response += f"\n   🔗 *View & Quote:* {rfq_link}\n\n"
            
            # Generate magic link for dashboard as well
            dashboard_magic = await generate_magic_link_for_vendor(sender, "/vendor/dashboard")
            if dashboard_magic.get("success"):
                dashboard_link = f"{BASE_URL}/magic-login?token={dashboard_magic['token']}"
            else:
                dashboard_link = f"{BASE_URL}/vendor/dashboard"
            
            response += f"━━━━━━━━━━━━━━━\n📱 *Dashboard:* {dashboard_link}\n\n🔑 _Click links for instant access_"
            return response
        except Exception as e:
            logger.error(f"RFQs command error: {str(e)}", exc_info=True)
            return f"⚠️ Error loading RFQs. Please try again or visit: {BASE_URL}/vendor/dashboard"
    
    # RFQ Details command - shows details and sends drawing if available
    if text.startswith("details ") or text.startswith("rfq ") or text.startswith("drawing "):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            return "⚠️ Please specify an RFQ ID. Example: *details abc123* or *rfq abc123*"
        
        rfq_id_search = parts[1].strip()
        
        # Find RFQ by partial ID match
        rfq = await db.rfqs.find_one(
            {"rfq_id": {"$regex": f"^rfq_{rfq_id_search}", "$options": "i"}},
            {"_id": 0}
        )
        
        if not rfq:
            # Try without prefix
            rfq = await db.rfqs.find_one(
                {"rfq_id": {"$regex": rfq_id_search, "$options": "i"}},
                {"_id": 0}
            )
        
        if not rfq:
            return f"⚠️ RFQ with ID '{rfq_id_search}' not found. Use *rfqs* to see available opportunities."
        
        rfq_id = rfq.get('rfq_id', '')
        urgency_label = URGENCY_LABELS.get(rfq.get("urgency", "normal"), "Normal")
        
        # Get AI analysis if available
        ai_analysis = rfq.get("ai_analysis", {})
        recommended_processes = ai_analysis.get("recommended_processes", [])
        part_complexity = ai_analysis.get("part_complexity", "")
        dimensions = ai_analysis.get("dimensions", {})
        
        # Build detailed response
        response = f"""📋 *RFQ Details*

*{rfq.get('title', 'Untitled')}*
{urgency_label}

📦 *Specifications:*
• Material: {rfq.get('material_type', 'N/A')}
• Quantity: {rfq.get('quantity', 'N/A')} units
• Tolerance: ±{rfq.get('tolerance', 'N/A')}mm
• Surface Finish: {rfq.get('surface_finish', 'N/A')}"""

        # Add dimensions if available
        if dimensions:
            dim_str = ""
            if dimensions.get("length"):
                dim_str += f"L: {dimensions['length']}mm "
            if dimensions.get("width"):
                dim_str += f"W: {dimensions['width']}mm "
            if dimensions.get("height"):
                dim_str += f"H: {dimensions['height']}mm"
            if dim_str:
                response += f"\n• Dimensions: {dim_str.strip()}"
        
        # Add AI insights
        if recommended_processes:
            response += f"\n\n🔧 *Recommended Processes:*\n• " + "\n• ".join(recommended_processes[:3])
        
        if part_complexity:
            complexity_emoji = {"simple": "🟢", "moderate": "🟡", "complex": "🔴"}.get(part_complexity.lower(), "⚪")
            response += f"\n\n{complexity_emoji} Complexity: {part_complexity.title()}"

        response += f"""

📝 *Description:*
{rfq.get('description', 'No description')[:200]}

📅 Deadline: {rfq.get('deadline', 'Not specified')}
🏷️ Status: {rfq.get('status', 'N/A').replace('_', ' ').title()}"""
        
        # Generate magic link for instant access to quote submission
        magic_result = await generate_magic_link_for_vendor(sender, f"/vendor/rfq/{rfq_id}")
        if magic_result.get("success"):
            quote_link = f"{BASE_URL}/magic-login?token={magic_result['token']}"
            response += f"""

🔗 *View & Submit Quote:*
{quote_link}

🔑 _Click link for instant access_"""
        else:
            response += f"""

🔗 *View & Submit Quote:*
{BASE_URL}/vendor/rfq/{rfq_id}"""
        
        # Check if drawings exist and send them
        drawing_ids = rfq.get("drawing_ids", [])
        if drawing_ids:
            response += f"\n\n📎 *{len(drawing_ids)} Drawing(s) attached* - Sending now..."
            
            # Send the text response first
            await whatsapp_service.send_text_message(sender, response)
            
            # Send each drawing
            from app.services.whatsapp_service import send_document_message, send_image_message
            
            for i, drawing_id in enumerate(drawing_ids[:3]):  # Limit to 3 drawings
                drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
                if drawing:
                    filename = drawing.get("filename", f"drawing_{i+1}.pdf")
                    file_type = drawing.get("file_type", "application/pdf")
                    
                    # Create a public URL for the drawing
                    drawing_url = f"{BASE_URL}/api/drawings/{drawing_id}/view?token=wa_temp"
                    
                    caption = f"📐 Drawing {i+1}/{len(drawing_ids)}: {filename}\nRFQ: {rfq.get('title', 'Untitled')[:30]}"
                    
                    # Check if it's an image or document
                    if file_type.startswith("image/"):
                        await send_image_message(sender, drawing_url, caption)
                    else:
                        await send_document_message(sender, drawing_url, filename, caption)
                    
                    # Small delay between files
                    await asyncio.sleep(1)
            
            return None  # Already sent messages
        
        return response
    
    # My Quotes command - expanded with Indian languages
    quotes_variants = ["my quotes", "quotes", "my bids", "my quote", "my cords", "my courts", 
                       "myquotes", "show quotes", "list quotes", "my quotations",
                       *hindi_quotes, *tamil_quotes, *telugu_quotes, *marathi_quotes, 
                       *bengali_quotes, *gujarati_quotes, *kannada_quotes, *punjabi_quotes]
    if intent == "quotes" or matches_command(text_normalized, quotes_variants):
        if not vendor:
            return f"""📭 *You're not registered as a vendor yet!*

To submit quotes, you need to register first.

📸 Send a photo of your *GST Certificate* to register!

Or visit: {BASE_URL}/register"""
        
        quotes = await db.quotes.find(
            {"vendor_id": vendor.get("vendor_id")},
            {"_id": 0}
        ).sort("created_at", -1).limit(5).to_list(length=5)
        
        if not quotes:
            return f"📭 You haven't submitted any quotes yet.\n\n🔗 Find RFQs: {BASE_URL}/vendor/dashboard"
        
        response = "💰 *Your Recent Quotes:*\n\n"
        for quote in quotes:
            quote_id = quote.get('quote_id', '')
            rfq_id = quote.get('rfq_id', '')
            status_emoji = {"pending": "⏳", "accepted": "✅", "rejected": "❌"}.get(quote.get("status", "pending"), "⏳")
            rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0, "title": 1})
            rfq_title = rfq.get("title", "Unknown") if rfq else "Unknown"
            
            response += f"{status_emoji} *{rfq_title[:25]}*\n"
            response += f"   Amount: ₹{quote.get('price', 0):,.2f}\n"
            response += f"   Lead Time: {quote.get('lead_time_days', 'N/A')} days\n"
            response += f"   Status: {quote.get('status', 'pending').title()}\n"
            response += f"   🔗 {BASE_URL}/vendor/rfq/{rfq_id}\n\n"
        
        response += f"📱 _View all quotes:_ {BASE_URL}/vendor/quotes"
        return response
    
    # My Orders command - expanded with Indian languages
    orders_variants = ["my orders", "orders", "active orders", "my order", "my odors", "my oders",
                       "myorders", "show orders", "list orders", "my auto", "my autos",
                       *hindi_orders, *tamil_orders, *telugu_orders, *marathi_orders,
                       *bengali_orders, *gujarati_orders, *kannada_orders, *punjabi_orders]
    if intent == "orders" or matches_command(text_normalized, orders_variants):
        if not vendor:
            return f"""📭 *You're not registered as a vendor yet!*

To receive orders, you need to register first.

📸 Send a photo of your *GST Certificate* to register!

Or visit: {BASE_URL}/register"""
        
        orders = await db.orders.find(
            {"vendor_id": vendor.get("vendor_id"), "status": {"$nin": ["cancelled", "completed"]}},
            {"_id": 0}
        ).sort("created_at", -1).limit(5).to_list(length=5)
        
        if not orders:
            return f"📭 No active orders.\n\n🔗 View dashboard: {BASE_URL}/vendor/dashboard"
        
        response = "📦 *Your Active Orders:*\n\n"
        for order in orders:
            order_id = order.get('order_id', '')
            status_emoji = {
                "pending_payment": "💳",
                "paid": "✅",
                "in_production": "🔨",
                "quality_check": "🔍",
                "dispatched": "🚚",
                "delivered": "📬"
            }.get(order.get("status", ""), "📋")
            
            response += f"{status_emoji} *PO #{order.get('po_number', 'N/A')}*\n"
            response += f"   Amount: ₹{order.get('total_amount', 0):,.2f}\n"
            response += f"   Status: {order.get('status', 'N/A').replace('_', ' ').title()}\n"
            response += f"   🔗 {BASE_URL}/vendor/order/{order_id}\n\n"
        
        response += f"📱 _View all orders:_ {BASE_URL}/vendor/orders"
        return response
    
    # Profile command - expanded with Indian languages
    profile_variants = ["profile", "my profile", "account", "my account", "my profil", "profil",
                        "show profile", "my details", "vendor profile",
                        *hindi_profile, *tamil_profile, *telugu_profile, *marathi_profile,
                        *bengali_profile, *gujarati_profile, *kannada_profile, *punjabi_profile]
    if intent == "profile" or matches_command(text_normalized, profile_variants):
        if not vendor:
            return f"""👤 *You're not registered as a vendor yet!*

To view your profile, you need to register first.

📸 Send a photo of your *GST Certificate* to register!

Or visit: {BASE_URL}/register"""
        
        profile_regional = get_bilingual_message("profile", vendor)
        company_regional = get_bilingual_message("company_name", vendor)
        
        response = f"""👤 *Your Vendor Profile*{profile_regional}

🏢 *{vendor.get('company_name', 'N/A')}*{company_regional}

📍 Location: {vendor.get('city', 'N/A')}, {vendor.get('state', '')}, {vendor.get('country', 'India')}
📮 Pincode: {vendor.get('pincode', 'N/A')}
📞 Phone: {vendor.get('phone', 'N/A')}
⭐ Rating: {vendor.get('rating', 0):.1f}/5
📊 Total Jobs: {vendor.get('total_jobs', 0)}
✅ Approved: {'Yes' if vendor.get('is_approved') else 'Pending'}

🔗 *Edit Profile:* {BASE_URL}/vendor/profile
🔗 *Manage Machines:* {BASE_URL}/vendor/machines"""
        return response
    
    # Email command - for adding/updating email address
    email_variants = ["email", "add email", "update email", "my email", "set email", "change email",
                      "ईमेल", "मेरा ईमेल", "ईमेल जोड़ें", "email id", "email address",
                      "ইমেল", "மின்னஞ்சல்", "ಇಮೇಲ್", "ఇమెయిల్", "ઈમેલ", "ਈਮੇਲ"]
    if matches_command(text_normalized, email_variants):
        # Check if already has email
        user_email = user.get("email", "") if user else ""
        vendor_email = vendor.get("contact_email", "")
        
        # Check if current email is a phone number (WhatsApp registration)
        has_real_email = False
        if user_email and "@" in user_email and not user_email.replace("@", "").isdigit():
            has_real_email = True
        if vendor_email and "@" in vendor_email:
            has_real_email = True
        
        if has_real_email:
            current_email = vendor_email if vendor_email and "@" in vendor_email else user_email
            return f"""📧 *Your Current Email*

Your registered email: *{current_email}*

To update, simply send your new email address.
Example: yourname@company.com"""
        
        # Set pending email state
        pending_email_inputs[sender] = {
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
        }
        
        lang_info = get_vendor_language(vendor)
        lang_code = lang_info.get("code", "hi")
        messages = EMAIL_REMINDER_MESSAGES.get(lang_code, EMAIL_REMINDER_MESSAGES.get("hi", {}))
        
        return f"""📧 *Add Your Email*
_{messages.get('reminder_msg', 'Please add your email ID')}_

Please send your email address.
Example: yourname@company.com

_{messages.get('why_needed', 'Required for RFQ match and quotation updates')}_

⏱️ _You have 10 minutes to respond_"""
    
    # Login command - Magic link for web dashboard auto-login
    login_variants = ["login", "web login", "dashboard", "open dashboard", "website", "web", 
                      "login link", "auto login", "sign in", "signin", "लॉगिन", "वेबसाइट",
                      "open web", "get link", "quick login", "magic link"]
    if matches_command(text_normalized, login_variants):
        if not vendor:
            return f"""🔗 *Web Login*

You're not registered yet. To access the web dashboard:

1️⃣ Register by sending your *GST Certificate* photo
2️⃣ Then type *login* to get your instant login link

Or register directly: {BASE_URL}/register"""
        
        # Generate magic link token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        # Store in MongoDB for persistence across instances
        await db.magic_link_tokens.insert_one({
            "token": token,
            "user_id": user.get("user_id") if user else vendor.get("user_id"),
            "phone": sender,
            "expires_at": expires_at.isoformat(),
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        login_url = f"{BASE_URL}/magic-login?token={token}"
        
        return f"""🔗 *Instant Web Login*

Click below to login to your dashboard instantly:

👉 {login_url}

⏱️ _Link expires in 15 minutes_
🔒 _One-time use only_

📱 Once logged in, you can:
• View & respond to RFQs
• Submit quotes
• Manage your machines
• Track orders"""
    
    # Machine Availability status update commands (handles "1 busy", "machine 1 busy", "all free" etc.)
    # MUST be checked BEFORE machines command to handle "machine 1 busy" pattern
    availability_set_pattern = re.match(r'(?:machine\s*)?(\d+)\s*(busy|available|free|maintenance|offline|engaged)', text_normalized)
    all_status_pattern = re.match(r'(?:all|sab|sabhi|सभी|सब)\s*(busy|available|free|maintenance|offline)', text_normalized)
    
    if availability_set_pattern or all_status_pattern:
        if not vendor:
            return f"""⚙️ *You're not registered as a vendor yet!*

To manage machines, you need to register first.

📸 Send a photo of your *GST Certificate* to register!

Or visit: {BASE_URL}/register"""
        
        machines = await db.machines.find(
            {"vendor_id": vendor.get("vendor_id"), "is_active": True},
            {"_id": 0, "machine_id": 1, "name": 1, "machine_type": 1, "availability_status": 1}
        ).sort("created_at", -1).limit(20).to_list(length=20)
        
        if not machines:
            return "⚠️ No machines found. Add machines first by sending a machine photo!"
        
        # Handle "all busy" / "all free" commands
        if all_status_pattern:
            new_status = all_status_pattern.group(1)
            if new_status == "free":
                new_status = "available"
            elif new_status == "busy":
                new_status = "engaged"
            
            # Update all machines
            result = await db.machines.update_many(
                {"vendor_id": vendor.get("vendor_id"), "is_active": True},
                {"$set": {"availability_status": new_status}}
            )
            
            status_emoji = {"available": "🟢", "engaged": "🔵", "maintenance": "🟡", "offline": "⚫"}.get(new_status, "🟢")
            status_labels = {"available": "Available", "engaged": "Busy/Engaged", "maintenance": "Maintenance", "offline": "Offline"}
            
            return f"""✅ *All Machines Updated!*

{status_emoji} Status: *{status_labels.get(new_status, new_status)}*
📊 Machines updated: {result.modified_count}

Type *machines* to view your machines."""
        
        # Handle individual machine status update
        if availability_set_pattern:
            machine_num = int(availability_set_pattern.group(1)) - 1
            new_status = availability_set_pattern.group(2)
            
            if new_status == "free":
                new_status = "available"
            elif new_status == "busy":
                new_status = "engaged"
            
            if 0 <= machine_num < len(machines):
                machine = machines[machine_num]
                await db.machines.update_one(
                    {"machine_id": machine["machine_id"]},
                    {"$set": {"availability_status": new_status}}
                )
                
                status_emoji = {"available": "🟢", "engaged": "🔵", "maintenance": "🟡", "offline": "⚫"}.get(new_status, "🟢")
                
                return f"""✅ *Status Updated!*

{status_emoji} *{machine['name']}*
   New Status: *{new_status.title()}*

Type *machines* to see all machines."""
            else:
                return f"⚠️ Invalid machine number. You have {len(machines)} machines (1-{len(machines)})."

    # Machines command - list vendor's machines with availability options
    machines_variants = ["machines", "my machines", "machine", "equipment", "show machines", "list machines",
                         "मशीन", "मेरी मशीन", "मशीनें", "उपकरण", "যন্ত্র", "இயந்திரங்கள்",
                         *hindi_machines, *tamil_machines, *telugu_machines, *marathi_machines,
                         *bengali_machines, *gujarati_machines, *kannada_machines, *punjabi_machines]
    if matches_command(text_normalized, machines_variants):
        if not vendor:
            return f"""🔧 *You're not registered as a vendor yet!*

To add machines, you need to register first.

📸 Send a photo of your *GST Certificate* to register!

Or visit: {BASE_URL}/register"""
        
        machines = await db.machines.find(
            {"vendor_id": vendor.get("vendor_id"), "is_active": True},
            {"_id": 0, "machine_id": 1, "name": 1, "machine_type": 1, "machine_category": 1, "brand": 1, "model": 1, "images": 1, "availability_status": 1}
        ).sort("created_at", -1).limit(15).to_list(length=15)
        
        if not machines:
            no_machines_regional = get_bilingual_message("no_machines", vendor)
            send_photo_regional = get_bilingual_message("send_machine_photo", vendor)
            
            return f"""🔧 *No Machines Added Yet*{no_machines_regional}

Add your machines to get matched with relevant RFQs!

📷 *Quick Add:* Send a photo of your machine{send_photo_regional}
✏️ *Manual Add:* {BASE_URL}/vendor/machines

Your machines help us match you with the right opportunities."""
        
        machine_count = len(machines)
        your_machines_regional = get_bilingual_message("your_machines", vendor)
        
        # Get bilingual instructions for availability
        lang_info = get_vendor_language(vendor)
        lang_code = lang_info.get("code", "hi")
        
        bilingual_status = {
            "hi": "_स्टेटस बदलें: '1 busy' या 'all free'_",
            "mr": "_स्टेटस बदला: '1 busy' किंवा 'all free'_",
            "gu": "_સ્ટેટસ બદલો: '1 busy' અથવા 'all free'_",
            "ta": "_நிலையை மாற்றவும்: '1 busy' அல்லது 'all free'_",
            "te": "_స్టేటస్ మార్చండి: '1 busy' లేదా 'all free'_",
            "kn": "_ಸ್ಥಿತಿ ಬದಲಾಯಿಸಿ: '1 busy' ಅಥವಾ 'all free'_",
            "bn": "_স্ট্যাটাস পরিবর্তন: '1 busy' বা 'all free'_",
            "pa": "_ਸਟੇਟਸ ਬਦਲੋ: '1 busy' ਜਾਂ 'all free'_"
        }
        
        response = f"🔧 *Your Machines ({machine_count}):*{your_machines_regional}\n\n"
        
        for i, m in enumerate(machines, 1):
            status_emoji = {"available": "🟢", "engaged": "🔵", "maintenance": "🟡", "offline": "⚫"}.get(m.get("availability_status", "available"), "🟢")
            status_text = m.get("availability_status", "available").title()
            has_image = "📷" if m.get("images") else ""
            
            response += f"*{i}.* {status_emoji} *{m.get('name', 'Unknown')}* ({status_text})\n"
            response += f"    {m.get('machine_type', 'N/A')} | {m.get('brand', '')} {m.get('model', '')} {has_image}\n\n"
        
        response += f"""━━━━━━━━━━━━━━━━━━━━━━
📊 *Set Availability:*
Reply: `1 busy` or `2 available` or `all free`
{bilingual_status.get(lang_code, "")}

*Statuses:* available, busy, maintenance, offline

━━━━━━━━━━━━━━━━━━━━━━
📷 _Send machine photo to add new_
🔗 *Manage:* {BASE_URL}/vendor/machines"""
        return response
    
    # Natural language query using AI
    if EMERGENT_LLM_KEY and len(text_normalized) > 5:
        try:
            # Use AI to understand and respond to the query
            llm = LlmChat(api_key=EMERGENT_LLM_KEY, model="gpt-4o-mini")
            
            # Get vendor's matched RFQs for context
            rfqs = await db.rfqs.find(
                {
                    "status": {"$in": ["submitted", "matching", "quoted"]},
                    "matched_vendors.vendor_id": vendor.get("vendor_id")
                },
                {"_id": 0, "rfq_id": 1, "title": 1, "material_type": 1, "quantity": 1, "urgency": 1, "deadline": 1, "description": 1}
            ).limit(10).to_list(length=10)
            
            rfq_context = "\n".join([
                f"- {r.get('title')} (ID: {r.get('rfq_id')[:8]}, Material: {r.get('material_type')}, Qty: {r.get('quantity')}, Urgency: {r.get('urgency')})"
                for r in rfqs
            ]) if rfqs else "No matching RFQs currently available."
            
            system_prompt = f"""You are OEMLinker's WhatsApp assistant helping vendor {vendor.get('company_name')}.
            
Available RFQs for this vendor:
{rfq_context}

Commands the user can use:
- rfqs: List matched RFQs
- details <id>: Get RFQ details  
- my quotes: View submitted quotes
- my orders: View active orders
- profile: View vendor profile
- help: Show all commands

Respond concisely in WhatsApp-friendly format. Use *bold* for emphasis.
If the user asks about specific RFQs, provide relevant details from the context.
Keep responses under 500 characters when possible."""

            llm.add_message(UserMessage(content=f"User query: {text}"))
            response = await asyncio.to_thread(
                llm.chat,
                system_prompt=system_prompt,
                max_tokens=300
            )
            
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logger.error(f"AI response error: {str(e)}")
            return "🤔 I couldn't understand that. Try using one of these commands:\n\n*rfqs* - View opportunities\n*help* - See all commands"
    
    # Default response
    return "🤔 I didn't understand that command. Type *help* to see available options."

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize services at startup"""
    # Initialize AWS S3 cloud storage
    try:
        from app.services.s3_storage_service import init_storage
        init_storage()
        logger.info("AWS S3 storage service initialized")
    except Exception as e:
        logger.warning(f"AWS S3 storage initialization failed (will use local fallback): {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
