from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
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
# Note: server.py maintains backward compatibility while modules are being refactored
import sys
sys.path.insert(0, str(Path(__file__).parent))

# These imports will gradually replace inline definitions
# from app.config import *
# from app.database import db
# from app.services.security import *
# from app.services.email_service import *
# from app.models import *
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
    picture: Optional[str] = None
    company_name: Optional[str] = None
    email_verified: bool = False
    created_at: str

class LoginRequest(BaseModel):
    email: EmailStr
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
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
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
    country: Optional[str] = None
    phone: Optional[str] = None
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
    price: float
    currency: str = "INR"
    lead_time_days: int
    notes: Optional[str] = None
    proposed_payment_terms: Optional[str] = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None
    is_selected: bool = False
    status: str = "pending"  # pending, accepted, rejected, expired
    created_at: str
    expires_at: str

class QuoteCreate(BaseModel):
    rfq_id: str
    price: float
    currency: str = "INR"
    lead_time_days: int
    notes: Optional[str] = None
    proposed_payment_terms: Optional[str] = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None

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
            picture=None,
            company_name=vendor_company_name,
            email_verified=False,
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
    
    # Sanitize email input
    email = sanitize_input(login_data.email.lower().strip())
    
    # Check if account is locked
    if is_account_locked(email):
        remaining = get_lockout_remaining(email)
        logger.warning(f"Login attempt on locked account: {email} from IP: {client_ip}")
        raise HTTPException(
            status_code=423, 
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {remaining // 60} minutes."
        )
    
    # Find user
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if not user:
        # Record failed attempt (use email even if not found to prevent enumeration)
        record_login_attempt(email, False)
        logger.warning(f"Failed login attempt for non-existent email: {email} from IP: {client_ip}")
        # Use same error message to prevent user enumeration
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(login_data.password, user.get("password_hash", "")):
        record_login_attempt(email, False)
        
        # Update failed attempts in DB
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
        # Generate and send OTP
        otp = generate_otp()
        store_otp(email, otp)
        
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
        asyncio.create_task(send_email_async(email, "🔐 Your OEMLinker Login Code", otp_html))
        
        logger.info(f"2FA OTP sent to: {email} from IP: {client_ip}")
        
        return {
            "requires_2fa": True,
            "message": "Verification code sent to your email",
            "email_hint": f"{email[:3]}***{email[email.index('@'):]}"
        }
    
    # No 2FA - proceed with normal login
    record_login_attempt(email, True)
    
    # Update user login info
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
            picture=user.get("picture"),
            company_name=user.get("company_name"),
            email_verified=user.get("email_verified", False),
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
        "picture": user.get("picture"),
        "company_name": user.get("company_name"),
        "email_verified": user.get("email_verified", False),
        "created_at": user["created_at"]
    }

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}

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
        
        # Send reset email
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
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"company_name": profile.company_name}}
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
    app_url = os.environ.get("APP_URL", "https://smart-procurement-27.preview.emergentagent.com")
    
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
    
    result = await db.machines.update_one(
        {"machine_id": machine_id, "vendor_id": vendor["vendor_id"]},
        {"$set": machine.model_dump()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    
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
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id, "buyer_id": user["user_id"]}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Read file content
    content = await file.read()
    file_base64 = base64.b64encode(content).decode('utf-8')
    
    drawing_id = f"drawing_{uuid.uuid4().hex[:12]}"
    drawing_doc = {
        "drawing_id": drawing_id,
        "rfq_id": rfq_id,
        "filename": file.filename,
        "file_type": file.content_type or "application/octet-stream",
        "file_size": len(content),
        "file_data": file_base64,
        "ai_analysis": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.drawings.insert_one(drawing_doc)
    
    # Add drawing ID to RFQ
    await db.rfqs.update_one(
        {"rfq_id": rfq_id},
        {"$push": {"drawing_ids": drawing_id}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"drawing_id": drawing_id, "filename": file.filename, "file_size": len(content)}

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
async def view_drawing(drawing_id: str, token: Optional[str] = None, request: Request = None):
    """View/download the actual drawing file - supports both Authorization header and query token"""
    # Try to authenticate via query token or header
    auth_token = token
    if not auth_token and request:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]
    
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = jwt.decode(auth_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
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
    """Download the drawing file as attachment"""
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
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
    
    file_type = drawing.get("file_type", "bin")
    filename = drawing.get("filename", f"drawing.{file_type}")
    
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
            file_data = drawing["file_data"]
            file_type = drawing.get("file_type", "").lower()
            filename = drawing.get("filename", "").lower()
            
            try:
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
    app_url = os.environ.get("APP_URL", "https://smart-procurement-27.preview.emergentagent.com")
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
            
            # Send WhatsApp notification
            vendor_profile = await db.vendors.find_one({"user_id": matched.get("user_id")}, {"_id": 0, "phone": 1})
            if vendor_profile and vendor_profile.get("phone") and whatsapp_service.is_configured():
                urgency_label = URGENCY_LABELS.get(rfq.get("urgency", "normal"), "🟢 Normal")
                wa_message = f"""🔔 *New RFQ Match on OEMLinker!*

📋 *{rfq.get('title', 'New RFQ')}*
{urgency_label}

📦 Material: {rfq.get('material_type', 'N/A')}
📏 Quantity: {rfq.get('quantity', 'N/A')} units
🎯 Match Score: {matched.get('suitability_score', 0)}%

🔗 View & Submit Quote:
https://oemlinker.com/vendor/rfq/{rfq_id}"""
                asyncio.create_task(whatsapp_service.send_text_message(vendor_profile["phone"], wa_message))
    
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
    
    quote_doc = {
        "quote_id": quote_id,
        "rfq_id": quote.rfq_id,
        "vendor_id": vendor["vendor_id"],
        "price": quote.price,
        "currency": quote.currency,
        "lead_time_days": quote.lead_time_days,
        "notes": quote.notes,
        "proposed_payment_terms": quote.proposed_payment_terms or "net_30",
        "payment_terms_notes": quote.payment_terms_notes,
        "is_selected": False,
        "status": "pending",
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
    app_url = os.environ.get("APP_URL", "https://smart-procurement-27.preview.emergentagent.com")
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
            wa_message = f"""💰 *New Quote Received!*

📋 *{rfq.get('title', 'Your RFQ')}*

🏭 Vendor: {vendor.get('company_name', 'Vendor')}
💵 Price: ₹{quote.price:,.2f}
📅 Lead Time: {quote.lead_time_days} days
⭐ Vendor Rating: {vendor.get('rating', 0):.1f}/5

🔗 Review Quote:
https://oemlinker.com/buyer/rfq/{quote.rfq_id}"""
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
                "app_url": f"{os.environ.get('APP_URL', 'https://smart-procurement-27.preview.emergentagent.com')}/vendor/rfq/{quote['rfq_id']}"
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
        buyer = await db.users.find_one({"user_id": negotiation["buyer_id"]}, {"_id": 0, "phone": 1})
        if buyer and buyer.get("phone"):
            action_emoji = {"accept": "✅", "counter": "🔄", "reject": "❌"}.get(response.action, "📨")
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
https://oemlinker.com/buyer/rfq/{quote['rfq_id']}"""
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
    app_url = os.environ.get("APP_URL", "https://smart-procurement-27.preview.emergentagent.com")
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
https://oemlinker.com/vendor/order/{order_id}"""
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
    app_url = os.environ.get("APP_URL", "https://smart-procurement-27.preview.emergentagent.com")
    
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
        
        wa_message = f"""{status_emoji} *Order Status Update*

🧾 *PO #{order.get('po_number', order_id[:8])}*
📋 {rfq_title}

📊 Status: *{status_label}*"""
        if note:
            wa_message += f"\n📝 Note: {note}"
        wa_message += f"""

🔗 View Order:
https://oemlinker.com/vendor/order/{order_id}"""

        # Notify vendor via WhatsApp
        if vendor and vendor.get("phone"):
            asyncio.create_task(whatsapp_service.send_text_message(vendor["phone"], wa_message))
        
        # Notify buyer via WhatsApp
        buyer = await db.users.find_one({"user_id": order["buyer_id"]}, {"_id": 0, "phone": 1})
        if buyer and buyer.get("phone"):
            buyer_wa_message = wa_message.replace("/vendor/order/", "/buyer/order/")
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    vendors = await db.vendors.find({"is_approved": False}, {"_id": 0}).to_list(100)
    return vendors

@api_router.post("/admin/vendors/{vendor_id}/approve")
async def approve_vendor(vendor_id: str, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    company_name: Optional[str] = None

@api_router.post("/admin/users")
async def admin_create_user(user_data: AdminUserCreate, user: dict = Depends(get_current_user)):
    """Admin creates a new user"""
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    allowed_fields = ["name", "role", "company_name"]
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Get related data
    buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "name": 1, "email": 1})
    drawings = await db.drawings.find({"rfq_id": rfq_id}, {"_id": 0, "file_data": 0}).to_list(20)
    quotes = await db.quotes.find({"rfq_id": rfq_id}, {"_id": 0}).to_list(50)
    
    # Enrich quotes with vendor info
    for quote in quotes:
        vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0, "company_name": 1})
        quote["vendor_info"] = vendor
    
    return {
        **rfq,
        "buyer_info": buyer,
        "drawings": drawings,
        "quotes": quotes
    }

@api_router.put("/admin/rfqs/{rfq_id}")
async def admin_update_rfq(rfq_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update RFQ details"""
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
    # Delete associated data
    await db.drawings.delete_many({"rfq_id": rfq_id})
    await db.quotes.delete_many({"rfq_id": rfq_id})
    await db.rfqs.delete_one({"rfq_id": rfq_id})
    
    return {"message": "RFQ deleted successfully"}

# ============== ADMIN - QUOTE MANAGEMENT ==============

@api_router.get("/admin/quotes")
async def admin_list_quotes(user: dict = Depends(get_current_user), status: Optional[str] = None):
    """List all quotes"""
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.quotes.delete_one({"quote_id": quote_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"message": "Quote deleted successfully"}

# ============== ADMIN - ORDER MANAGEMENT ==============

@api_router.get("/admin/orders")
async def admin_list_orders(user: dict = Depends(get_current_user), status: Optional[str] = None):
    """List all orders"""
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.orders.delete_one({"order_id": order_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Order deleted successfully"}

# ============== ADMIN - DRAWING MANAGEMENT ==============

@api_router.get("/admin/drawings")
async def admin_list_drawings(user: dict = Depends(get_current_user)):
    """List all drawings (without file data)"""
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    drawing = await db.drawings.find_one({"drawing_id": drawing_id}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
    return drawing

@api_router.delete("/admin/drawings/{drawing_id}")
async def admin_delete_drawing(drawing_id: str, user: dict = Depends(get_current_user)):
    """Delete a drawing"""
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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

@api_router.put("/admin/vendors/{vendor_id}")
async def admin_update_vendor(vendor_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update vendor details"""
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    
    # Allowed vendor fields
    vendor_fields = ["company_name", "description", "phone", "website", "address", "city", "country", 
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
    """List all machines, optionally filtered by vendor"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
        }
    }
    return categories

@api_router.post("/admin/machines")
async def admin_create_machine(request: Request, user: dict = Depends(get_current_user)):
    """Create a machine for any vendor (admin)"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    vendor_id = body.get("vendor_id")
    
    if not vendor_id:
        raise HTTPException(status_code=400, detail="vendor_id is required")
    
    vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    machine_id = f"machine_{uuid.uuid4().hex[:12]}"
    machine_doc = {
        "machine_id": machine_id,
        "vendor_id": vendor_id,
        "name": body.get("name", ""),
        "machine_type": body.get("machine_type", ""),
        "machine_category": body.get("machine_category", ""),
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
        # General
        "materials": body.get("materials", []),
        "materials_supported": body.get("materials_supported", []),
        "is_active": body.get("is_active", True),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.machines.insert_one(machine_doc)
    return {"machine_id": machine_id, "message": "Machine created successfully"}

@api_router.get("/admin/machines/{machine_id}")
async def admin_get_machine(machine_id: str, user: dict = Depends(get_current_user)):
    """Get machine details (admin)"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    machine = await db.machines.find_one({"machine_id": machine_id}, {"_id": 0})
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get vendor info
    vendor = await db.vendors.find_one({"vendor_id": machine["vendor_id"]}, {"_id": 0, "company_name": 1})
    machine["vendor_name"] = vendor.get("company_name") if vendor else "Unknown"
    
    return machine

@api_router.put("/admin/machines/{machine_id}")
async def admin_update_machine(machine_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update any machine (admin)"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
    
    result = await db.machines.update_one({"machine_id": machine_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    return {"message": "Machine updated successfully"}

@api_router.delete("/admin/machines/{machine_id}")
async def admin_delete_machine(machine_id: str, user: dict = Depends(get_current_user)):
    """Delete any machine (admin)"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.machines.delete_one({"machine_id": machine_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    return {"message": "Machine deleted successfully"}

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
    if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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
        if user["role"] != UserRole.ADMIN:
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
    if user["role"] != UserRole.ADMIN:
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

@api_router.post("/whatsapp/send")
async def send_whatsapp_message(
    data: WhatsAppMessageRequest,
    user: dict = Depends(get_current_user)
):
    """Send a WhatsApp message (Admin only)"""
    if user.get("role") != "admin":
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
    if user.get("role") != "admin":
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

@api_router.post("/whatsapp/notify-rfq")
async def notify_vendors_new_rfq(
    rfq_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Send WhatsApp notifications to matched vendors about a new RFQ
    Called after RFQ matching is complete
    """
    if user.get("role") not in ["admin", "buyer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not whatsapp_service.is_configured():
        return {"success": False, "error": "WhatsApp not configured", "notified_count": 0}
    
    # Get RFQ details
    rfq = await db.rfqs.find_one({"rfq_id": rfq_id}, {"_id": 0})
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    
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
        
        # Prepare message
        urgency_label = URGENCY_LABELS.get(rfq.get("urgency", "normal"), "Normal")
        message = f"""🔔 *New RFQ Match on OEMLinker!*

📋 *{rfq.get('title', 'New RFQ')}*
{urgency_label}

📦 Material: {rfq.get('material_type', 'N/A')}
📏 Quantity: {rfq.get('quantity', 'N/A')} units
🎯 Match Score: {match.get('match_score', 0)}%

💡 Reply with *"details {rfq_id[:8]}"* to learn more or login to OEMLinker to submit your quote.

Type *"help"* for more commands."""

        result = await whatsapp_service.send_text_message(phone, message)
        
        if result.get("success"):
            notified_count += 1
            logger.info(f"WhatsApp notification sent to vendor {vendor_id}")
        else:
            errors.append({"vendor_id": vendor_id, "error": result.get("error")})
    
    return {
        "success": True,
        "notified_count": notified_count,
        "total_matched": len(rfq.get("matched_vendors", [])),
        "errors": errors if errors else None
    }

# Store processed message IDs to prevent duplicates (with TTL)
processed_message_ids = {}  # {message_id: timestamp}
MESSAGE_ID_TTL_SECONDS = 300  # 5 minutes

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
        
        # Find vendor by phone number
        vendor = await db.vendors.find_one(
            {"phone": {"$regex": sender[-10:]}},  # Match last 10 digits
            {"_id": 0}
        )
        
        user = None
        if vendor:
            user = await db.users.find_one({"user_id": vendor.get("user_id")}, {"_id": 0})
        
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
        # Handle image messages (GST certificate upload for registration)
        elif msg_type == "image" and parsed.get("image_url"):
            # Check if user is already registered
            if vendor:
                if whatsapp_service.is_configured():
                    await whatsapp_service.send_text_message(
                        sender,
                        "📷 Image received! You're already registered.\n\nType *help* to see available commands."
                    )
                return {"status": "ok"}
            
            # Process image for GST certificate extraction
            response_message = await process_gst_certificate_image(parsed.get("image_url"), sender)
            if response_message and whatsapp_service.is_configured():
                await whatsapp_service.send_text_message(sender, response_message)
            return {"status": "ok"}
        else:
            text = parsed.get("text", "").strip().lower()
        
        if not sender or not text:
            logger.warning(f"WhatsApp: Missing sender or text. Sender: {sender}, Text: '{text}'")
            return {"status": "ok"}
        
        logger.info(f"WhatsApp processing command: '{text}' from {sender[:6]}***")
        
        # Process commands
        response_message = await process_whatsapp_command(text, sender, vendor, user)
        
        logger.info(f"WhatsApp response generated: {response_message[:100] if response_message else 'None'}...")
        
        # Send text response
        if response_message and whatsapp_service.is_configured():
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
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


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
        ai_response = await chat.send_async(user_message)
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
        
        # Send confirmation message before registration
        if whatsapp_service.is_configured():
            await whatsapp_service.send_text_message(
                sender,
                f"""📋 *GST Number Extracted*

GSTIN: *{extracted_text}*

⏳ Verifying and registering your account..."""
            )
        
        # Process registration with the extracted GSTIN
        registration_result = await process_whatsapp_registration(sender, extracted_text)
        return registration_result
        
    except Exception as e:
        logger.error(f"GST certificate processing error: {str(e)}")
        return f"""❌ *Processing Failed*

An error occurred while processing your GST certificate.

Please try again or register manually at https://oemlinker.com/register

You can also type your GST number directly:
*register YOUR_GST_NUMBER*

Contact support@oemlinker.com for assistance."""



async def process_whatsapp_registration(sender: str, gst_number: str) -> str:
    """Process vendor registration via WhatsApp using GST number"""
    import secrets
    import string
    
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
        state_code = gst_data.get("stcd", "")
        address_parts = []
        if gst_data.get("pradr", {}).get("adr"):
            address_parts.append(gst_data["pradr"]["adr"])
        city = gst_data.get("pradr", {}).get("loc", "")
        state = gst_data.get("pradr", {}).get("stcd", "")
        pincode = gst_data.get("pradr", {}).get("pncd", "")
        
        # Generate email from GST (temporary)
        email_base = gst_number.lower().replace(" ", "")
        temp_email = f"{email_base}@oemlinker.vendor"
        
        # Generate temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # Create user account
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        password_hash = pwd_context.hash(temp_password)
        
        user_doc = {
            "user_id": user_id,
            "email": temp_email,
            "password_hash": password_hash,
            "name": company_name,
            "role": UserRole.VENDOR,
            "is_verified": True,  # Auto-verify for WhatsApp registration
            "phone": sender,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "registered_via": "whatsapp"
        }
        
        await db.users.insert_one(user_doc)
        
        # Create vendor profile
        vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
        vendor_doc = {
            "vendor_id": vendor_id,
            "user_id": user_id,
            "company_name": company_name,
            "gstin": gst_number,
            "gst_verified": True,
            "gst_data": gst_data,
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
        
        logger.info(f"New vendor registered via WhatsApp: {company_name} (GST: {gst_number})")
        
        return f"""🎉 *Registration Successful!*

Welcome to *OEMLinker*, {company_name}!

✅ *Account Created*
🏢 Company: {company_name}
📋 GST: {gst_number}
📍 Location: {city}, {state}
📞 Phone: {sender}

🔐 *Login Credentials:*
Email: {temp_email}
Password: {temp_password}

⚠️ *Important:*
1. Please update your email at https://oemlinker.com/vendor/profile
2. Add your machines to start receiving RFQ matches
3. Your account is pending admin approval

💡 *Next Steps:*
• Type *help* to see available commands
• Type *rfqs* to view matching opportunities

🔗 Complete your profile:
https://oemlinker.com/vendor/profile"""

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
        
        for cmd in commands:
            # Direct match
            if cmd in input_text:
                return True
            # Reverse check (short input matches longer command)
            if input_text in cmd:
                return True
            # No-space match for voice errors like "myorders"
            if cmd.replace(" ", "") in input_no_spaces:
                return True
            # Word-based match - check if command words appear in the sentence
            cmd_words = cmd.split()
            if len(cmd_words) > 1:
                # For multi-word commands, check if all words appear
                if all(word in input_text for word in cmd_words):
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
    # Hindi variants
    hindi_rfq = ["आरएफक्यू", "काम", "नौकरी", "अवसर", "काम दिखाओ", "आर्डर दिखाओ", "कोटेशन", "रिक्वेस्ट"]
    hindi_orders = ["मेरे ऑर्डर", "ऑर्डर", "आर्डर", "मेरा आर्डर", "ऑर्डर दिखाओ", "आर्डर दिखाओ"]
    hindi_quotes = ["मेरे कोट्स", "कोट्स", "मेरा कोट", "बोली", "मेरी बोली", "कोटेशन"]
    hindi_profile = ["प्रोफाइल", "मेरी प्रोफाइल", "अकाउंट", "खाता", "मेरा खाता"]
    hindi_help = ["मदद", "सहायता", "हेल्प", "मेन्यू", "शुरू"]
    
    # Tamil variants
    tamil_rfq = ["வேலை", "வாய்ப்பு", "கோரிக்கை"]
    tamil_orders = ["என் ஆர்டர்", "ஆர்டர்கள்", "ஆர்டர்"]
    tamil_quotes = ["என் மேற்கோள்", "மேற்கோள்கள்"]
    tamil_profile = ["சுயவிவரம்", "என் சுயவிவரம்"]
    tamil_help = ["உதவி", "மெனு"]
    
    # Telugu variants  
    telugu_rfq = ["పని", "అవకాశం", "అభ్యర్థన"]
    telugu_orders = ["నా ఆర్డర్లు", "ఆర్డర్లు"]
    telugu_quotes = ["నా కోట్స్", "కోట్స్"]
    telugu_profile = ["ప్రొఫైల్", "నా ప్రొఫైల్"]
    telugu_help = ["సహాయం", "మెను"]
    
    # Marathi variants
    marathi_rfq = ["काम", "संधी", "विनंती"]
    marathi_orders = ["माझे ऑर्डर", "ऑर्डर"]
    marathi_quotes = ["माझे कोट्स", "कोट्स"]
    marathi_profile = ["प्रोफाइल", "माझी प्रोफाइल"]
    marathi_help = ["मदत", "मेनू"]
    
    # Bengali variants
    bengali_rfq = ["কাজ", "সুযোগ", "অনুরোধ"]
    bengali_orders = ["আমার অর্ডার", "অর্ডার"]
    bengali_quotes = ["আমার কোট", "কোট"]
    bengali_profile = ["প্রোফাইল", "আমার প্রোফাইল"]
    bengali_help = ["সাহায্য", "মেনু"]
    
    # Gujarati variants
    gujarati_rfq = ["કામ", "તક", "વિનંતી"]
    gujarati_orders = ["મારા ઓર્ડર", "ઓર્ડર"]
    gujarati_quotes = ["મારા કોટ્સ", "કોટ્સ"]
    gujarati_profile = ["પ્રોફાઇલ", "મારી પ્રોફાઇલ"]
    gujarati_help = ["મદદ", "મેનુ"]
    
    # Kannada variants
    kannada_rfq = ["ಕೆಲಸ", "ಅವಕಾಶ"]
    kannada_orders = ["ನನ್ನ ಆರ್ಡರ್", "ಆರ್ಡರ್"]
    kannada_quotes = ["ನನ್ನ ಕೋಟ್ಸ್", "ಕೋಟ್ಸ್"]
    kannada_profile = ["ಪ್ರೊಫೈಲ್"]
    kannada_help = ["ಸಹಾಯ", "ಮೆನು"]
    
    # Punjabi variants
    punjabi_rfq = ["ਕੰਮ", "ਮੌਕਾ"]
    punjabi_orders = ["ਮੇਰੇ ਆਰਡਰ", "ਆਰਡਰ"]
    punjabi_quotes = ["ਮੇਰੇ ਕੋਟਸ", "ਕੋਟਸ"]
    punjabi_profile = ["ਪ੍ਰੋਫਾਈਲ"]
    punjabi_help = ["ਮਦਦ", "ਮੀਨੂ"]
    
    # Help command - expanded with Indian languages
    help_variants = ["help", "hi", "hello", "menu", "start", "hey", "helo", "assist", "assistance",
                     *hindi_help, *tamil_help, *telugu_help, *marathi_help,
                     *bengali_help, *gujarati_help, *kannada_help, *punjabi_help]
    if intent == "help" or matches_command(text_normalized, help_variants):
        if vendor:
            return f"""👋 Welcome to *OEMLinker*, {vendor.get('company_name', 'Vendor')}!

📋 *Available Commands:*

*rfqs* - View open RFQs matching your capabilities
*details <rfq_id>* - Get details of a specific RFQ
*my quotes* - View your submitted quotes
*my orders* - View your active orders
*profile* - View your vendor profile
*help* - Show this menu

🎤 *Voice Search:* Send a voice message to search!

💡 You can also ask questions in natural language!

Example: "Show me urgent RFQs for steel machining" """
        else:
            return """👋 Welcome to *OEMLinker*!

Your phone number is not linked to a vendor account.

📝 *Register via WhatsApp:*
Send your GST number to register instantly!
Example: _register 27AABCU9603R1ZM_

Or visit oemlinker.com to register manually.

Need help? Type *help* or contact support@oemlinker.com"""

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
            return """📝 *Vendor Registration*

To register, please send your *GST Number* in the following format:

_register 27AABCU9603R1ZM_

Or just send the GST number directly.

Your account will be created automatically with your business details from GSTIN database."""

    # Must be a registered vendor for other commands
    if not vendor:
        return """⚠️ Your phone is not linked to a vendor account.

📝 *Quick Registration:*
Send your GST number to register!
Example: _27AABCU9603R1ZM_

Or visit https://oemlinker.com to register."""
    
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
        # Get matched RFQs for this vendor
        rfqs = await db.rfqs.find(
            {
                "status": {"$in": ["submitted", "matching", "quoted"]},
                "matched_vendors.vendor_id": vendor.get("vendor_id")
            },
            {"_id": 0, "rfq_id": 1, "title": 1, "material_type": 1, "quantity": 1, "urgency": 1, "matched_vendors": 1}
        ).sort("created_at", -1).limit(5).to_list(length=5)
        
        if not rfqs:
            return f"📭 No matching RFQs found at the moment.\n\n🔗 View all RFQs: {BASE_URL}/vendor/dashboard"
        
        response = "📋 *Your Matched RFQs:*\n\n"
        for rfq in rfqs:
            rfq_id = rfq.get('rfq_id', '')
            urgency_emoji = {"urgent": "🔴", "high": "🟠", "normal": "🟢", "low": "🔵"}.get(rfq.get("urgency", "normal"), "🟢")
            # Find match score for this vendor
            match_score = 0
            for m in rfq.get("matched_vendors", []):
                if m.get("vendor_id") == vendor.get("vendor_id"):
                    match_score = m.get("match_score", 0)
                    break
            
            response += f"{urgency_emoji} *{rfq.get('title', 'Untitled')[:30]}*\n"
            response += f"   Material: {rfq.get('material_type', 'N/A')} | Qty: {rfq.get('quantity', 'N/A')}\n"
            response += f"   Match: {match_score}%\n"
            response += f"   🔗 {BASE_URL}/vendor/rfq/{rfq_id}\n\n"
        
        response += f"📱 _View all on dashboard:_ {BASE_URL}/vendor/dashboard"
        return response
    
    # RFQ Details command
    if text.startswith("details ") or text.startswith("rfq "):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            return "⚠️ Please specify an RFQ ID. Example: *details abc123*"
        
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
        
        response = f"""📋 *RFQ Details*

*{rfq.get('title', 'Untitled')}*
{urgency_label}

📦 *Specifications:*
• Material: {rfq.get('material_type', 'N/A')}
• Quantity: {rfq.get('quantity', 'N/A')} units
• Tolerance: ±{rfq.get('tolerance', 'N/A')}mm
• Surface Finish: {rfq.get('surface_finish', 'N/A')}

📝 *Description:*
{rfq.get('description', 'No description')[:200]}

📅 Deadline: {rfq.get('deadline', 'Not specified')}
🏷️ Status: {rfq.get('status', 'N/A').replace('_', ' ').title()}

🔗 *View & Submit Quote:*
{BASE_URL}/vendor/rfq/{rfq_id}"""
        
        return response
    
    # My Quotes command - expanded with Indian languages
    quotes_variants = ["my quotes", "quotes", "my bids", "my quote", "my cords", "my courts", 
                       "myquotes", "show quotes", "list quotes", "my quotations",
                       *hindi_quotes, *tamil_quotes, *telugu_quotes, *marathi_quotes, 
                       *bengali_quotes, *gujarati_quotes, *kannada_quotes, *punjabi_quotes]
    if intent == "quotes" or matches_command(text_normalized, quotes_variants):
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
        response = f"""👤 *Your Vendor Profile*

🏢 *{vendor.get('company_name', 'N/A')}*

📍 Location: {vendor.get('city', 'N/A')}, {vendor.get('country', 'N/A')}
📞 Phone: {vendor.get('phone', 'N/A')}
⭐ Rating: {vendor.get('rating', 0):.1f}/5
📊 Total Jobs: {vendor.get('total_jobs', 0)}
✅ Approved: {'Yes' if vendor.get('is_approved') else 'Pending'}

🔗 *Edit Profile:* {BASE_URL}/vendor/profile
🔗 *Manage Machines:* {BASE_URL}/vendor/machines"""
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
