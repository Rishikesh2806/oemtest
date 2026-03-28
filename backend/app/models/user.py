"""
User-related Pydantic Models
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
import re


class UserRole:
    BUYER = "buyer"
    VENDOR = "vendor"
    ADMIN = "admin"
    STAFF = "staff"
    
    BASE_ROLES = [BUYER, VENDOR, ADMIN, STAFF]


class UserBase(BaseModel):
    email: EmailStr
    name: str
    company_name: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: str = UserRole.BUYER
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in [UserRole.BUYER, UserRole.VENDOR, UserRole.ADMIN]:
            raise ValueError('Invalid role')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    # Vendor-specific fields (optional, filled during registration)
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    pincode: Optional[str] = None
    website: Optional[str] = None
    year_established: Optional[int] = None
    employee_count: Optional[str] = None
    certifications: Optional[list] = []
    specializations: Optional[list] = []
    
    @field_validator('gstin')
    @classmethod
    def validate_gstin(cls, v):
        if v:
            pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
            if not re.match(pattern, v.upper()):
                raise ValueError('Invalid GSTIN format')
        return v.upper() if v else v


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    custom_role: Optional[str] = None
    secondary_roles: List[str] = []
    company_name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False
    created_at: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    website: Optional[str] = None
    profile_picture: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    email: EmailStr
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class EmailVerificationRequest(BaseModel):
    token: str


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str
    pending_token: str


class TwoFactorToggle(BaseModel):
    enabled: bool
    password: str  # Require password confirmation
