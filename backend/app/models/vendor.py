"""
Vendor Models
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


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
    past_experiences: List[dict] = []
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
    part_type: Optional[str] = None
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
    # GST fields
    gstin: Optional[str] = None
    gst_verified: Optional[bool] = None
    gst_status: Optional[str] = None
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    taxpayer_type: Optional[str] = None
    constitution: Optional[str] = None
    gst_registration_date: Optional[str] = None
