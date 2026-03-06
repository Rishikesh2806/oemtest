"""
OEMLinker Backend - Main Application Entry Point
Refactored modular structure with backward compatibility

This file initializes the FastAPI app with middleware and mounts routers.
The actual server.py imports from here for backward compatibility.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application"""
    app = FastAPI(
        title="OEMLinker API",
        description="AI-Powered On-Demand Manufacturing Marketplace",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


# Create the application instance
app = create_app()
