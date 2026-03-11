"""
Vendor Service - Vendor profile operations
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from app.database import db


async def get_vendor_by_user_id(user_id: str) -> Optional[dict]:
    """Get vendor profile by user ID"""
    return await db.vendors.find_one({"user_id": user_id}, {"_id": 0})


async def get_vendor_by_id(vendor_id: str) -> Optional[dict]:
    """Get vendor profile by vendor ID"""
    return await db.vendors.find_one({"vendor_id": vendor_id}, {"_id": 0})


async def create_vendor_profile(user_id: str, data: dict) -> dict:
    """Create a new vendor profile"""
    vendor_id = f"vendor_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    vendor_doc = {
        "vendor_id": vendor_id,
        "user_id": user_id,
        "company_name": data.get("company_name", ""),
        "description": data.get("description", ""),
        "address": data.get("address", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "pincode": data.get("pincode", ""),
        "country": data.get("country", "India"),
        "phone": data.get("phone", ""),
        "contact_email": data.get("contact_email", ""),
        "website": data.get("website", ""),
        "certifications": data.get("certifications", []),
        "industries": data.get("industries", []),
        "materials_handled": data.get("materials_handled", []),
        "is_approved": False,
        "rating": 0.0,
        "total_jobs": 0,
        "created_at": now,
        "updated_at": now
    }
    
    await db.vendors.insert_one(vendor_doc)
    
    # Update user with company name
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"company_name": data.get("company_name", "")}}
    )
    
    return vendor_doc


async def update_vendor_profile(vendor_id: str, data: dict) -> bool:
    """Update an existing vendor profile"""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.vendors.update_one(
        {"vendor_id": vendor_id},
        {"$set": data}
    )
    return result.modified_count > 0


async def get_approved_vendors(limit: int = 100) -> List[dict]:
    """Get all approved vendors"""
    return await db.vendors.find(
        {"is_approved": True}, {"_id": 0}
    ).limit(limit).to_list(limit)


async def get_pending_vendors(limit: int = 100) -> List[dict]:
    """Get all vendors pending approval"""
    return await db.vendors.find(
        {"is_approved": False}, {"_id": 0}
    ).limit(limit).to_list(limit)


async def approve_vendor(vendor_id: str) -> bool:
    """Approve a vendor"""
    result = await db.vendors.update_one(
        {"vendor_id": vendor_id},
        {"$set": {"is_approved": True, "approved_at": datetime.now(timezone.utc).isoformat()}}
    )
    return result.modified_count > 0


async def reject_vendor(vendor_id: str, reason: str = "") -> bool:
    """Reject a vendor"""
    result = await db.vendors.update_one(
        {"vendor_id": vendor_id},
        {"$set": {
            "is_approved": False, 
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": reason
        }}
    )
    return result.modified_count > 0
