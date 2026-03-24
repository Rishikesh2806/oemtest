# Routes Package - API Endpoints

from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import route modules
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.vendor import router as vendor_router
from app.routes.orders import router as orders_router
from app.routes.chatbot import router as chatbot_router
from app.routes.google_auth import router as google_auth_router

# Include routers - these will be prefixed by the main app's /api
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(vendor_router)
api_router.include_router(orders_router)
api_router.include_router(chatbot_router)
api_router.include_router(google_auth_router)
