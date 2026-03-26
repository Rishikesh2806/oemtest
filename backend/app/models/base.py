"""
Base Models and Common Classes
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
import re


class UserRole:
    BUYER = "buyer"
    VENDOR = "vendor"
    ADMIN = "admin"
    STAFF = "staff"
    
    BASE_ROLES = [BUYER, VENDOR, ADMIN, STAFF]

SECONDARY_ROLES = ["supervisor", "qa", "logistics", "operations", "inspector"]


class UserBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    name: str
    role: str = UserRole.BUYER


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    role: str
    secondary_roles: List[str] = []
    picture: Optional[str] = None
    company_name: Optional[str] = None
    email_verified: bool = False
    phone_login: bool = False
    contact_email: Optional[str] = None
    created_at: str


class LoginRequest(BaseModel):
    email: str  # Can be email or phone number
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RFQStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    MATCHING = "matching"
    QUOTED = "quoted"
    NEGOTIATING = "negotiating"
    PO_ISSUED = "po_issued"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SupplyType:
    ONE_TIME = "one_time"
    RECURRING = "recurring"


class UrgencyLevel:
    STANDARD = "standard"
    PRIORITY = "priority"
    URGENT = "urgent"


class PaymentTerms:
    ADVANCE = "100_advance"
    PARTIAL = "50_advance_50_delivery"
    NET30 = "net_30"
    NET60 = "net_60"
    LC = "letter_of_credit"
    ESCROW = "escrow"


class Incoterms:
    EXW = "EXW"
    FCA = "FCA"
    FOB = "FOB"
    CIF = "CIF"
    DDP = "DDP"
    DAP = "DAP"


class NotificationType:
    RFQ_MATCH = "rfq_match"
    QUOTE_RECEIVED = "quote_received"
    QUOTE_ACCEPTED = "quote_accepted"
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    MESSAGE_RECEIVED = "message_received"


class OrderStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PRODUCTION = "in_production"
    QUALITY_CHECK = "quality_check"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DisputeStatus:
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class DisputeType:
    QUALITY = "quality"
    DELIVERY = "delivery"
    PAYMENT = "payment"
    COMMUNICATION = "communication"
    OTHER = "other"
