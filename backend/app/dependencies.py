"""
Shared Dependencies - Authentication and authorization helpers
"""
from fastapi import HTTPException, Request
import jwt
import logging

from app.database import db
from app.config import JWT_SECRET, JWT_ALGORITHM

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> dict:
    """
    Extract and validate user from JWT token or session cookie.
    This is the main authentication dependency used across all routes.
    """
    auth_header = request.headers.get("Authorization", "")
    session_token = request.cookies.get("session_token")
    
    token = None
    
    # Check Bearer token first
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    # Fallback to session cookie
    elif session_token:
        session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
        if session:
            user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
            if user:
                return user
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user_optional(request: Request) -> dict | None:
    """
    Optional authentication - returns None if not authenticated instead of raising error.
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def require_admin(user: dict) -> dict:
    """Check if user is admin, raise HTTPException if not"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_vendor(user: dict) -> dict:
    """Check if user is vendor, raise HTTPException if not"""
    if user.get("role") != "vendor":
        raise HTTPException(status_code=403, detail="Vendor access required")
    return user


async def require_buyer(user: dict) -> dict:
    """Check if user is buyer, raise HTTPException if not"""
    if user.get("role") != "buyer":
        raise HTTPException(status_code=403, detail="Buyer access required")
    return user
