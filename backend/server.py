from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import JSONResponse
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

@api_router.post("/rfqs/{rfq_id}/analyze")
async def analyze_rfq_drawings(rfq_id: str, user: dict = Depends(get_current_user)):
    """Use AI to analyze the uploaded drawings"""
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
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"analysis_{rfq_id}_{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert manufacturing engineer analyzing engineering drawings. 
            Extract and provide the following information in JSON format:
            {
                "overall_dimensions": {"length": float, "width": float, "height": float, "unit": "mm"},
                "critical_tolerances": [{"feature": string, "tolerance": float, "unit": "mm"}],
                "holes": [{"diameter": float, "depth": float, "quantity": int}],
                "threads": [{"type": string, "size": string, "quantity": int}],
                "material_specs": string or null,
                "surface_finish": string or null,
                "recommended_processes": [string],
                "complexity_score": int (1-10),
                "estimated_machining_time_hours": float,
                "special_requirements": [string]
            }
            If you cannot determine a value, use null. Be precise with measurements."""
        ).with_model("openai", "gpt-5.2")
        
        # Create image content for vision analysis
        image_content = ImageContent(image_base64=drawing["file_data"])
        
        user_message = UserMessage(
            text=f"""Analyze this engineering drawing and extract manufacturing specifications.
            
            RFQ Context:
            - Title: {rfq['title']}
            - Material Type: {rfq['material_type']}
            - Required Tolerance: {rfq['tolerance']} mm
            - Quantity: {rfq['quantity']}
            
            Please provide a detailed analysis in the JSON format specified.""",
            image_contents=[image_content]
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
    """Match RFQ with capable vendors based on machine capabilities"""
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
                "company_name": "Precision CNC Works",
                "suitability_score": 92,
                "matching_machines": ["CNC Milling Center", "5-Axis VMC"],
                "materials_match": True,
                "tolerance_capable": True,
                "location": "Mumbai, India",
                "rating": 4.8,
                "total_jobs": 156
            },
            {
                "vendor_id": "demo_vendor_2",
                "company_name": "MetalTech Industries",
                "suitability_score": 87,
                "matching_machines": ["VMC 850", "CNC Lathe"],
                "materials_match": True,
                "tolerance_capable": True,
                "location": "Pune, India",
                "rating": 4.6,
                "total_jobs": 89
            },
            {
                "vendor_id": "demo_vendor_3",
                "company_name": "Global Machining Solutions",
                "suitability_score": 81,
                "matching_machines": ["HMC 500", "Turn-Mill Center"],
                "materials_match": True,
                "tolerance_capable": True,
                "location": "Chennai, India",
                "rating": 4.5,
                "total_jobs": 234
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
    
    ai_analysis = rfq.get("ai_analysis", {})
    required_tolerance = rfq.get("tolerance", 0.1)
    required_material = rfq.get("material_type", "").lower()
    
    matched_vendors = []
    
    for vendor in vendors:
        # Get vendor's machines
        machines = await db.machines.find(
            {"vendor_id": vendor["vendor_id"], "is_active": True},
            {"_id": 0}
        ).to_list(50)
        
        if not machines:
            continue
        
        # Calculate suitability score
        score = 50  # Base score
        matching_machines = []
        tolerance_capable = False
        materials_match = False
        
        for machine in machines:
            # Check tolerance capability
            if machine.get("tolerance_capability", 1.0) <= required_tolerance:
                tolerance_capable = True
                score += 10
            
            # Check material compatibility
            machine_materials = [m.lower() for m in machine.get("materials_supported", [])]
            if required_material in machine_materials or not machine_materials:
                materials_match = True
                score += 10
            
            # Check dimensions if available
            dims = ai_analysis.get("overall_dimensions", {})
            if dims.get("length") and machine.get("max_x"):
                if dims["length"] <= machine["max_x"]:
                    score += 5
            
            if tolerance_capable or materials_match:
                matching_machines.append(f"{machine['machine_type']} - {machine['brand']} {machine['model']}")
        
        if matching_machines:
            # Add vendor experience bonus
            score += min(vendor.get("total_jobs", 0) / 10, 15)
            score += vendor.get("rating", 0) * 3
            
            matched_vendors.append({
                "vendor_id": vendor["vendor_id"],
                "company_name": vendor["company_name"],
                "suitability_score": min(int(score), 100),
                "matching_machines": matching_machines[:3],
                "materials_match": materials_match,
                "tolerance_capable": tolerance_capable,
                "location": f"{vendor.get('city', '')}, {vendor.get('country', '')}",
                "rating": vendor.get("rating", 0),
                "total_jobs": vendor.get("total_jobs", 0)
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
        "total_orders": total_orders
    }

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
