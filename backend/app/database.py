"""
Database Connection and Setup
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URL, DB_NAME

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

async def shutdown_db():
    """Close database connection on shutdown"""
    client.close()
