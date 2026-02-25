from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'offoadex_secret_key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 168  # 7 days

# Create the main app
app = FastAPI(title="Offoadex API", version="1.0.0")

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

def get_email_template(template_type: str, data: dict) -> tuple:
    """Get email subject and HTML content for various notification types"""
    
    templates = {
        "vendor_matched": {
            "subject": f"New RFQ Match: {data.get('rfq_title', 'New Opportunity')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">New RFQ Match!</h1>
                </div>
                <div style="padding: 30px; background: #f8fafc;">
                    <p style="font-size: 16px; color: #334155;">Hello {data.get('vendor_name', 'Vendor')},</p>
                    <p style="font-size: 16px; color: #334155;">You've been matched to a new RFQ based on your machine capabilities!</p>
                    
                    <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #f97316;">
                        <h3 style="color: #1e293b; margin-top: 0;">{data.get('rfq_title', 'RFQ')}</h3>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Material:</strong> {data.get('material', 'N/A')}</p>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Quantity:</strong> {data.get('quantity', 'N/A')}</p>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Buyer:</strong> {data.get('buyer_name', 'N/A')}</p>
                        <p style="color: #64748b; margin: 5px 0;"><strong>Your Match Score:</strong> {data.get('match_score', 'N/A')}%</p>
                    </div>
                    
                    <p style="font-size: 16px; color: #334155;">Log in to Offoadex to view details and submit your quote.</p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{data.get('app_url', '#')}" style="background: #f97316; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">View RFQ</a>
                    </div>
                </div>
                <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p>Offoadex - AI-Powered Manufacturing Marketplace</p>
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
                    <p>Offoadex - AI-Powered Manufacturing Marketplace</p>
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
                    <p>Offoadex - AI-Powered Manufacturing Marketplace</p>
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
                    <p>Offoadex - AI-Powered Manufacturing Marketplace</p>
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
                    <p style="font-size: 16px; color: #334155;">You have a new message on Offoadex.</p>
                    
                    <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #8b5cf6;">
                        <p style="color: #64748b; margin: 0 0 10px 0;"><strong>From:</strong> {data.get('sender_name', 'N/A')}</p>
                        <p style="color: #1e293b; font-style: italic;">"{data.get('message_preview', '')[:200]}..."</p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{data.get('app_url', '#')}" style="background: #8b5cf6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Message</a>
                    </div>
                </div>
                <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p>Offoadex - AI-Powered Manufacturing Marketplace</p>
                </div>
            </div>
            """
        }
    }
    
    template = templates.get(template_type, {})
    return template.get("subject", "Offoadex Notification"), template.get("html", "<p>Notification</p>")

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

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    role: str
    picture: Optional[str] = None
    company_name: Optional[str] = None
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
    is_approved: bool = False
    rating: float = 0.0
    total_jobs: int = 0
    created_at: str

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

class Machine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    machine_id: str
    vendor_id: str
    machine_type: str  # CNC, VMC, HMC, Laser, Press Brake, etc.
    brand: str
    model: str
    max_x: Optional[float] = None  # mm
    max_y: Optional[float] = None  # mm
    max_z: Optional[float] = None  # mm
    max_diameter: Optional[float] = None  # mm
    tonnage: Optional[float] = None
    tolerance_capability: float = 0.1  # mm
    axis_config: Optional[str] = None  # 3-axis, 5-axis, etc.
    materials_supported: List[str] = []
    monthly_capacity_hours: int = 160
    is_active: bool = True
    created_at: str

class MachineCreate(BaseModel):
    machine_type: str
    brand: str
    model: str
    max_x: Optional[float] = None
    max_y: Optional[float] = None
    max_z: Optional[float] = None
    max_diameter: Optional[float] = None
    tonnage: Optional[float] = None
    tolerance_capability: float = 0.1
    axis_config: Optional[str] = None
    materials_supported: List[str] = []
    monthly_capacity_hours: int = 160

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
    status: str = RFQStatus.DRAFT
    drawing_ids: List[str] = []
    ai_analysis: Optional[Dict[str, Any]] = None
    matched_vendors: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str

class RFQCreate(BaseModel):
    title: str
    description: Optional[str] = None
    material_type: str
    quantity: int = 1
    tolerance: float = 0.1
    surface_finish: Optional[str] = None
    supply_type: str = SupplyType.VENDOR_MATERIAL
    deadline: Optional[str] = None

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
    currency: str = "USD"
    lead_time_days: int
    notes: Optional[str] = None
    is_selected: bool = False
    status: str = "pending"  # pending, accepted, rejected, expired
    created_at: str
    expires_at: str

class QuoteCreate(BaseModel):
    rfq_id: str
    price: float
    currency: str = "USD"
    lead_time_days: int
    notes: Optional[str] = None

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
    currency: str = "USD"
    status: str = OrderStatus.PENDING_PAYMENT
    payment_status: str = "pending"
    tracking_updates: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str

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

# ============== AUTH ROUTES ==============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "role": user_data.role,
        "password_hash": hash_password(user_data.password),
        "picture": None,
        "company_name": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_jwt_token(user_id, user_data.email, user_data.role)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            picture=None,
            company_name=None,
            created_at=user_doc["created_at"]
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    user = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
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
            created_at=user["created_at"]
        )
    )

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
        "created_at": user["created_at"]
    }

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}

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
    result = await db.vendors.update_one(
        {"user_id": user["user_id"]},
        {"$set": profile.model_dump()}
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
    """Use AI to analyze the uploaded drawings (supports PDF, PNG, JPG)"""
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
    
    # Get first drawing for analysis
    drawing = await db.drawings.find_one({"drawing_id": rfq["drawing_ids"][0]}, {"_id": 0})
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        # Convert PDF to image if needed
        file_data = drawing["file_data"]
        file_type = drawing.get("file_type", "").lower()
        filename = drawing.get("filename", "").lower()
        
        if "pdf" in file_type or filename.endswith(".pdf"):
            logger.info(f"Converting PDF to image for analysis: {filename}")
            try:
                file_data = convert_pdf_to_image_base64(file_data)
            except Exception as pdf_err:
                logger.error(f"PDF conversion error: {pdf_err}")
                raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(pdf_err)}")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"analysis_{rfq_id}_{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert manufacturing engineer analyzing engineering drawings. 
            CAREFULLY examine every detail in the drawing including dimension callouts, tolerances, notes, and title blocks.
            
            Extract and provide the following information in JSON format:
            {
                "overall_dimensions": {"length": float, "width": float, "height": float, "unit": "mm"},
                "critical_tolerances": [{"feature": string, "tolerance": float, "unit": "mm"}],
                "holes": [{"diameter": float, "depth": float or null for THRU, "quantity": int}],
                "threads": [{"type": string, "size": string, "quantity": int}],
                "material_specs": string or null,
                "surface_finish": string or null,
                "recommended_processes": [string] - BE SPECIFIC based on features seen,
                "complexity_score": int (1-10),
                "estimated_machining_time_hours": float,
                "special_requirements": [string],
                "max_dimension_mm": float - the largest dimension for machine envelope matching
            }
            
            IMPORTANT: Read ALL dimension callouts carefully. Look at the title block for material specs.
            For recommended_processes, list SPECIFIC operations needed (e.g., "5-axis milling for complex contour", "Wire EDM for tight slots")."""
        ).with_model("openai", "gpt-5.2")
        
        # Create image content for vision analysis
        image_content = ImageContent(image_base64=file_data)
        
        user_message = UserMessage(
            text=f"""CAREFULLY analyze this engineering drawing and extract ALL manufacturing specifications.
            
            RFQ Context:
            - Title: {rfq['title']}
            - Material Type: {rfq['material_type']}
            - Required Tolerance: {rfq['tolerance']} mm
            - Quantity: {rfq['quantity']}
            
            Please provide a detailed analysis in the JSON format specified.""",
            file_contents=[image_content]
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
        
        # Update drawing with analysis
        await db.drawings.update_one(
            {"drawing_id": drawing["drawing_id"]},
            {"$set": {"ai_analysis": ai_analysis}}
        )
        
        # Update RFQ with analysis
        await db.rfqs.update_one(
            {"rfq_id": rfq_id},
            {"$set": {
                "ai_analysis": ai_analysis,
                "status": RFQStatus.MATCHING,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"message": "Analysis complete", "analysis": ai_analysis}
        
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        # Provide fallback analysis
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
        
        return {"message": "Analysis complete with fallback", "analysis": fallback_analysis}

# ============== VENDOR MATCHING ==============

@api_router.post("/rfqs/{rfq_id}/match")
async def match_vendors(rfq_id: str, user: dict = Depends(get_current_user)):
    """Match RFQ with capable vendors based on AI-extracted drawing data and machine capabilities"""
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
    
    # Extract requirements from AI analysis
    ai_analysis = rfq.get("ai_analysis", {})
    dims = ai_analysis.get("overall_dimensions", {})
    recommended_processes = ai_analysis.get("recommended_processes", [])
    
    # Get max dimension from drawing for machine envelope check
    max_dimension = ai_analysis.get("max_dimension_mm")
    if not max_dimension:
        # Calculate from dimensions
        dim_values = [dims.get("length"), dims.get("width"), dims.get("height")]
        dim_values = [d for d in dim_values if d]
        max_dimension = max(dim_values) if dim_values else None
    
    required_tolerance = rfq.get("tolerance", 0.1)
    required_material = rfq.get("material_type", "").lower()
    
    # Extract material from AI if available
    ai_material = (ai_analysis.get("material_specs") or "").lower()
    
    logger.info(f"Matching RFQ {rfq_id}: dims={dims}, tolerance={required_tolerance}, material={required_material}, max_dim={max_dimension}")
    logger.info(f"Recommended processes: {recommended_processes}")
    
    matched_vendors = []
    
    for vendor in vendors:
        # Get vendor's machines
        machines = await db.machines.find(
            {"vendor_id": vendor["vendor_id"], "is_active": True},
            {"_id": 0}
        ).to_list(50)
        
        if not machines:
            continue
        
        # Track capabilities across all machines
        matching_machines = []
        tolerance_capable = False
        materials_match = False
        dimension_capable = False
        process_matches = []
        has_suitable_machine = False
        
        for machine in machines:
            machine_type_lower = machine.get("machine_type", "").lower()
            machine_name = f"{machine['machine_type']} - {machine['brand']} {machine['model']}"
            machine_score = 0
            machine_process_match = False
            
            # CRITICAL: First check if machine type matches required processes
            # Welding machines should NOT match milling/turning jobs
            is_welding_machine = "weld" in machine_type_lower
            is_cnc_machine = any(k in machine_type_lower for k in ["cnc", "mill", "vmc", "hmc", "turn", "lathe", "drill", "edm", "grind"])
            
            # Check if this machine can perform ANY of the recommended processes
            for process in recommended_processes:
                process_lower = process.lower()
                
                # Milling processes
                if any(keyword in process_lower for keyword in ["milling", "mill", "face", "pocket", "profile", "slot"]):
                    if any(k in machine_type_lower for k in ["mill", "vmc", "hmc", "5-axis", "5 axis", "cnc"]) and not is_welding_machine:
                        machine_process_match = True
                        if "5-axis" in machine_type_lower or "5 axis" in machine_type_lower:
                            machine_score += 30
                            process_matches.append("5-Axis Milling")
                        else:
                            machine_score += 25
                            process_matches.append("CNC Milling")
                        break
                
                # Turning processes
                elif any(keyword in process_lower for keyword in ["turn", "lathe", "bore", "ream", "facing"]):
                    if any(k in machine_type_lower for k in ["turn", "lathe"]) and not is_welding_machine:
                        machine_process_match = True
                        machine_score += 25
                        process_matches.append("CNC Turning")
                        break
                
                # Drilling/Tapping
                elif any(keyword in process_lower for keyword in ["drill", "tap", "thread", "hole"]):
                    if is_cnc_machine and not is_welding_machine:
                        machine_process_match = True
                        machine_score += 15
                        process_matches.append("Drilling/Tapping")
                        break
                
                # Grinding
                elif any(keyword in process_lower for keyword in ["grind", "surface finish"]):
                    if "grind" in machine_type_lower and not is_welding_machine:
                        machine_process_match = True
                        machine_score += 20
                        process_matches.append("Grinding")
                        break
                
                # EDM
                elif any(keyword in process_lower for keyword in ["edm", "wire cut", "spark"]):
                    if "edm" in machine_type_lower:
                        machine_process_match = True
                        machine_score += 20
                        process_matches.append("EDM")
                        break
                
                # Welding - only for welding jobs
                elif any(keyword in process_lower for keyword in ["weld", "fabricat", "join"]):
                    if is_welding_machine:
                        machine_process_match = True
                        machine_score += 25
                        process_matches.append("Welding")
                        break
            
            # SKIP this machine if it doesn't match any required process
            if not machine_process_match:
                continue
            
            has_suitable_machine = True
            
            # Additional scoring for suitable machines only
            
            # TOLERANCE CHECK (+20 points)
            machine_tolerance = machine.get("tolerance_capability", 1.0)
            if machine_tolerance <= required_tolerance:
                tolerance_capable = True
                machine_score += 20
            
            # MATERIAL CHECK (+15 points)
            machine_materials = [m.lower() for m in machine.get("materials_supported", [])]
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
            
            # DIMENSION/ENVELOPE CHECK (+15 points)
            if max_dimension:
                max_x = machine.get("max_x") or 0
                max_y = machine.get("max_y") or 0
                max_z = machine.get("max_z") or 0
                max_dia = machine.get("max_diameter") or 0
                machine_max = max(max_x, max_y, max_z, max_dia)
                
                if machine_max >= max_dimension:
                    dimension_capable = True
                    machine_score += 15
            
            # EXPERIENCE BONUS (+10 points max)
            vendor_jobs = vendor.get("total_jobs", 0)
            vendor_rating = vendor.get("rating", 0)
            experience_score = min((vendor_jobs / 50) + (vendor_rating * 1.5), 10)
            machine_score += experience_score
            
            matching_machines.append({
                "name": machine_name,
                "score": machine_score,
                "tolerance": machine_tolerance,
                "envelope": f"{machine.get('max_x', 0)}x{machine.get('max_y', 0)}x{machine.get('max_z', 0)}mm"
            })
        
        # Only include vendor if they have at least one suitable machine
        if has_suitable_machine and matching_machines:
            # Sort machines by score
            matching_machines.sort(key=lambda x: x["score"], reverse=True)
            best_machine_score = matching_machines[0]["score"]
            
            # Final score capped at 100
            final_score = min(int(best_machine_score), 100)
            
            matched_vendors.append({
                "vendor_id": vendor["vendor_id"],
                "user_id": vendor["user_id"],  # Include user_id for chat functionality
                "company_name": vendor["company_name"],
                "suitability_score": final_score,
                "matching_machines": [m["name"] for m in matching_machines[:3]],
                "machine_details": matching_machines[:3],
                "materials_match": materials_match,
                "tolerance_capable": tolerance_capable,
                "dimension_capable": dimension_capable,
                "process_matches": list(set(process_matches))[:3],
                "location": f"{vendor.get('city', '')}, {vendor.get('country', '')}",
                "rating": vendor.get("rating", 0),
                "total_jobs": vendor.get("total_jobs", 0),
                "certifications": vendor.get("certifications", [])[:3]
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
    
    # Send email notifications to matched vendors (non-blocking)
    app_url = os.environ.get("APP_URL", "https://vendor-matching-demo.preview.emergentagent.com")
    buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "name": 1})
    
    for matched in matched_vendors:
        vendor_user = await db.users.find_one({"user_id": matched.get("user_id")}, {"_id": 0, "email": 1, "name": 1})
        if vendor_user and vendor_user.get("email"):
            email_data = {
                "vendor_name": vendor_user.get("name", "Vendor"),
                "rfq_title": rfq.get("title", "New RFQ"),
                "material": rfq.get("material_type", "N/A"),
                "quantity": rfq.get("quantity", "N/A"),
                "buyer_name": buyer.get("name", "Buyer") if buyer else "Buyer",
                "match_score": matched.get("suitability_score", 0),
                "app_url": f"{app_url}/vendor/dashboard"
            }
            subject, html = get_email_template("vendor_matched", email_data)
            asyncio.create_task(send_email_async(vendor_user["email"], subject, html))
    
    return {"matched_vendors": matched_vendors, "total_matches": len(matched_vendors)}

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
    app_url = os.environ.get("APP_URL", "https://vendor-matching-demo.preview.emergentagent.com")
    buyer = await db.users.find_one({"user_id": rfq["buyer_id"]}, {"_id": 0, "email": 1, "name": 1})
    if buyer and buyer.get("email"):
        email_data = {
            "buyer_name": buyer.get("name", "Buyer"),
            "rfq_title": rfq.get("title", "Your RFQ"),
            "vendor_name": vendor.get("company_name", "Vendor"),
            "price": f"{quote.price:.2f}",
            "lead_time": quote.lead_time_days,
            "app_url": f"{app_url}/rfq/{quote.rfq_id}"
        }
        subject, html = get_email_template("quote_received", email_data)
        asyncio.create_task(send_email_async(buyer["email"], subject, html))
    
    return Quote(**quote_doc)

@api_router.get("/quotes/rfq/{rfq_id}")
async def get_quotes_for_rfq(rfq_id: str, user: dict = Depends(get_current_user)):
    quotes = await db.quotes.find({"rfq_id": rfq_id}, {"_id": 0}).to_list(50)
    
    # Enrich with vendor info
    for quote in quotes:
        vendor = await db.vendors.find_one({"vendor_id": quote["vendor_id"]}, {"_id": 0})
        if vendor:
            quote["vendor_name"] = vendor.get("company_name", "Unknown")
            quote["vendor_rating"] = vendor.get("rating", 0)
    
    return quotes

@api_router.get("/quotes/vendor")
async def get_vendor_quotes(user: dict = Depends(get_current_user)):
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        return []
    
    quotes = await db.quotes.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).to_list(100)
    return quotes

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
    
    # Create order
    order_id = f"order_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
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
        "tracking_updates": [
            {"status": "Order Created", "timestamp": now, "note": "Quote accepted, awaiting payment"}
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
    
    return {"message": "Status updated", "status": new_status}

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
    
    # Delete associated data
    await db.vendors.delete_many({"user_id": user_id})
    await db.machines.delete_many({"vendor_id": {"$regex": user_id}})
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.users.delete_one({"user_id": user_id})
    
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

# ============== DASHBOARD STATS ==============

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

# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "Offoadex API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

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
