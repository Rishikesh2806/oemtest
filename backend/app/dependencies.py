"""
FastAPI Dependencies - Authentication, Database access
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, Request, Depends
import jwt

from app.database import db
from app.core.auth import JWT_SECRET, JWT_ALGORITHM


async def get_current_user(request: Request) -> dict:
    """Get the current authenticated user from session or JWT token"""
    # Check cookie first
    token = request.cookies.get("session_token")
    
    # Then check Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Try session token from OAuth first
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
    """Get current user or return None if not authenticated"""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require the current user to be an admin"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_vendor(user: dict = Depends(get_current_user)) -> dict:
    """Require the current user to be a vendor"""
    if user.get("role") != "vendor":
        raise HTTPException(status_code=403, detail="Vendor access required")
    return user


async def require_buyer(user: dict = Depends(get_current_user)) -> dict:
    """Require the current user to be a buyer"""
    if user.get("role") != "buyer":
        raise HTTPException(status_code=403, detail="Buyer access required")
    return user
