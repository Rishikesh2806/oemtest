"""
User Service - User account operations
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.database import db
from app.core.auth import hash_password


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by user ID"""
    return await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    return await db.users.find_one({"email": email.lower().strip()}, {"_id": 0})


async def get_user_by_phone(phone: str) -> Optional[dict]:
    """Get user by phone number"""
    # Normalize phone number
    phone_normalized = phone.replace("+", "").replace(" ", "").replace("-", "")
    phone_10digit = phone_normalized[-10:] if len(phone_normalized) >= 10 else phone_normalized
    
    return await db.users.find_one({
        "$or": [
            {"email": phone_10digit},
            {"email": f"91{phone_10digit}"},
            {"phone": phone_10digit},
            {"phone": f"91{phone_10digit}"},
            {"phone": f"+91{phone_10digit}"}
        ]
    }, {"_id": 0})


async def create_user(data: dict) -> dict:
    """Create a new user"""
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "user_id": user_id,
        "email": data["email"].lower().strip(),
        "name": data["name"],
        "role": data.get("role", "buyer"),
        "password_hash": hash_password(data["password"]),
        "picture": None,
        "company_name": data.get("company_name"),
        "email_verified": False,
        "created_at": now,
        "last_login": now,
        "login_count": 1
    }
    
    await db.users.insert_one(user_doc)
    return user_doc


async def update_user(user_id: str, data: dict) -> bool:
    """Update user data"""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": data}
    )
    return result.modified_count > 0


async def update_user_password(user_id: str, new_password: str) -> bool:
    """Update user password"""
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "password_hash": hash_password(new_password),
            "security_settings.password_changed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return result.modified_count > 0


async def verify_user_email(user_id: str) -> bool:
    """Mark user email as verified"""
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"email_verified": True}}
    )
    return result.modified_count > 0


async def record_login(user_id: str):
    """Record a successful login"""
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {"last_login": datetime.now(timezone.utc).isoformat()},
            "$inc": {"login_count": 1}
        }
    )
