"""
Vendor Routes - Vendor profile and experience management
- Profile CRUD
- Past experiences management
- Vendor lookup by ID
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging

from app.database import db
from app.routes.auth import get_current_user
from app.models.vendor import VendorProfile, VendorProfileCreate, PastExperience
from app.models.base import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendors", tags=["Vendors"])


# ============== VENDOR PROFILE ROUTES ==============

@router.post("/profile", response_model=VendorProfile)
async def create_vendor_profile(profile: VendorProfileCreate, user: dict = Depends(get_current_user)):
    """Create a new vendor profile"""
    # Check if user is a vendor (by role or has vendor profile intent)
    if user.get("role") != UserRole.VENDOR and user.get("role") != "vendor":
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
    
    logger.info(f"Vendor profile created: {vendor_id} for user {user['user_id']}")
    return VendorProfile(**vendor_doc)


@router.get("/profile")
async def get_vendor_profile(user: dict = Depends(get_current_user)):
    """Get current user's vendor profile"""
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    return vendor


@router.put("/profile")
async def update_vendor_profile(profile: VendorProfileCreate, user: dict = Depends(get_current_user)):
    """Update current user's vendor profile"""
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


@router.get("/list")
async def list_vendors(approved_only: bool = True):
    """List all vendors (optionally only approved ones)"""
    query = {"is_approved": True} if approved_only else {}
    vendors = await db.vendors.find(query, {"_id": 0}).to_list(100)
    return vendors


# ============== VENDOR PAST EXPERIENCE ==============
# NOTE: These routes MUST come BEFORE /vendors/{vendor_id} routes to avoid path conflicts

@router.post("/experiences")
async def add_past_experience(experience: PastExperience, user: dict = Depends(get_current_user)):
    """Add a past experience to vendor profile"""
    user_role = user.get("role", "")
    if user_role != "vendor" and user_role != UserRole.VENDOR:
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


@router.get("/experiences")
async def get_my_experiences(user: dict = Depends(get_current_user)):
    """Get vendor's past experiences"""
    user_role = user.get("role", "")
    if user_role != "vendor" and user_role != UserRole.VENDOR:
        raise HTTPException(status_code=403, detail="Only vendors can view their experiences")
    
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0, "past_experiences": 1})
    if not vendor:
        # Return empty if no vendor profile yet
        return {"experiences": []}
    
    return {"experiences": vendor.get("past_experiences", [])}


@router.delete("/experiences/{experience_id}")
async def delete_experience(experience_id: str, user: dict = Depends(get_current_user)):
    """Delete a past experience"""
    user_role = user.get("role", "")
    if user_role != "vendor" and user_role != UserRole.VENDOR:
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


# ============== VENDOR LOOKUP ==============

@router.get("/{vendor_id}")
async def get_vendor_by_id(vendor_id: str):
    """Get vendor by ID (public endpoint)"""
    vendor = await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("/{vendor_id}/full")
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
