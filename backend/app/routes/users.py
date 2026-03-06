"""
User Routes - User profile management
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

from app.database import db
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["User"])


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


@router.get("/profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    db_user = await db.users.find_one(
        {"user_id": user["user_id"]}, 
        {"_id": 0, "password_hash": 0}
    )
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/profile")
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
    
    db_user = await db.users.find_one(
        {"user_id": user["user_id"]}, 
        {"_id": 0, "password_hash": 0}
    )
    return db_user
