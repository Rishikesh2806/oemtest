# Routes Package - API Endpoints

from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import route modules
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router

# Include routers - these will be prefixed by the main app's /api
api_router.include_router(auth_router)
api_router.include_router(users_router)
