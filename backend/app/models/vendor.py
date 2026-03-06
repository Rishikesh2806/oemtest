"""
Vendor-related Pydantic Models
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class PastExperience(BaseModel):
    """Vendor's past project experience for matching"""
    experience_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    material: Optional[str] = None
    part_type: Optional[str] = None
    industry: Optional[str] = None
    processes_used: List[str] = []
    quantity: Optional[int] = None
    year: Optional[int] = None
    client_name: Optional[str] = None
    image_url: Optional[str] = None


class VendorProfile(BaseModel):
    vendor_id: str
    user_id: str
    company_name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    pincode: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    year_established: Optional[int] = None
    employee_count: Optional[str] = None
    certifications: List[str] = []
    specializations: List[str] = []
    is_approved: bool = False
    rating: float = 0.0
    total_jobs: int = 0
    past_experiences: List[PastExperience] = []
    created_at: str = ""
    updated_at: str = ""


class VendorProfileCreate(BaseModel):
    company_name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    pincode: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    year_established: Optional[int] = None
    employee_count: Optional[str] = None
    certifications: List[str] = []
    specializations: List[str] = []
