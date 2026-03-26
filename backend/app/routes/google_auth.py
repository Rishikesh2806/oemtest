"""
Google OAuth Routes - Google Sign-In integration
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import uuid
import httpx
import logging
from urllib.parse import urlencode

from app.database import db
from app.services.security import create_jwt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleTokenRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None


@router.get("/login")
async def google_login(redirect_uri: Optional[str] = None):
    """Initiate Google OAuth flow - returns the Google auth URL"""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    default_redirect = os.environ.get("GOOGLE_REDIRECT_URI", "")
    
    if not client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Use provided redirect_uri or default
    callback_uri = redirect_uri or default_redirect
    
    # Build Google OAuth URL
    params = {
        "client_id": client_id,
        "redirect_uri": callback_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    return {"auth_url": auth_url}


@router.post("/callback")
async def google_callback(token_request: GoogleTokenRequest):
    """Handle Google OAuth callback - exchange code for tokens and create/login user"""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    default_redirect = os.environ.get("GOOGLE_REDIRECT_URI", "")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    redirect_uri = token_request.redirect_uri or default_redirect
    
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": token_request.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            if token_response.status_code != 200:
                logger.error(f"Google token error: {token_response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"Google userinfo error: {userinfo_response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user info from Google")
            
            google_user = userinfo_response.json()
        
        # Extract user info
        google_id = google_user.get("id")
        email = google_user.get("email")
        name = google_user.get("name")
        picture = google_user.get("picture")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Check if user exists (by google_id or email)
        existing_user = await db.users.find_one(
            {"$or": [{"google_id": google_id}, {"email": email}]},
            {"_id": 0}
        )
        
        if existing_user:
            # Update existing user with Google info
            user_id = existing_user["user_id"]
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "google_id": google_id,
                    "picture": picture,
                    "email_verified": True,
                    "last_login": datetime.now(timezone.utc).isoformat(),
                    "login_method": "google"
                },
                "$inc": {"login_count": 1}}
            )
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        else:
            # Create new user
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            user = {
                "user_id": user_id,
                "email": email,
                "name": name,
                "google_id": google_id,
                "picture": picture,
                "role": "",
                "secondary_roles": [],
                "email_verified": True,
                "login_method": "google",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": datetime.now(timezone.utc).isoformat(),
                "login_count": 1
            }
            await db.users.insert_one(user)
            if "_id" in user:
                del user["_id"]
            logger.info(f"New user created via Google: {email}")
        
        # Create JWT token
        jwt_token = create_jwt_token(user["user_id"], user["email"], user.get("role", ""))
        
        # Determine redirect based on base role only
        role = user.get("role", "")
        if not role:
            redirect_path = "/select-role"
        elif role == "buyer":
            redirect_path = "/buyer/dashboard"
        elif role == "vendor":
            redirect_path = "/vendor/dashboard"
        elif role == "staff":
            redirect_path = "/staff/dashboard"
        elif role == "admin":
            redirect_path = "/admin/dashboard"
        else:
            redirect_path = "/dashboard"
        
        return {
            "success": True,
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "name": user.get("name"),
                "role": user.get("role", ""),
                "secondary_roles": user.get("secondary_roles", []),
                "picture": user.get("picture"),
                "email_verified": True,
                "is_new_user": not existing_user
            },
            "redirect_path": redirect_path
        }
        
    except httpx.RequestError as e:
        logger.error(f"Google OAuth request error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with Google")
    except Exception as e:
        logger.error(f"Google OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def google_callback_redirect(code: str, state: Optional[str] = None):
    """Handle direct redirect from Google (GET request)"""
    # This endpoint handles the redirect from Google
    # It returns HTML that posts the code to the frontend
    frontend_url = os.environ.get("FRONTEND_URL") or os.environ.get("APP_URL")
    if not frontend_url:
        raise HTTPException(status_code=500, detail="FRONTEND_URL or APP_URL not configured")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Completing Sign In...</title>
        <style>
            body {{ 
                font-family: system-ui, -apple-system, sans-serif;
                display: flex; 
                justify-content: center; 
                align-items: center; 
                height: 100vh; 
                margin: 0;
                background: #f8fafc;
            }}
            .loader {{
                text-align: center;
                color: #64748b;
            }}
            .spinner {{
                width: 40px;
                height: 40px;
                border: 3px solid #e2e8f0;
                border-top: 3px solid #f97316;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 16px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="loader">
            <div class="spinner"></div>
            <p>Completing sign in...</p>
        </div>
        <script>
            // Send the code to the parent window or redirect
            const code = "{code}";
            if (window.opener) {{
                window.opener.postMessage({{ type: 'google-auth', code: code }}, '*');
                window.close();
            }} else {{
                // Redirect to frontend with code
                window.location.href = "{frontend_url}/auth/google/callback?code=" + code;
            }}
        </script>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)
