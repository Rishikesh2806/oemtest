"""
WhatsApp Logging Service
Tracks all WhatsApp API interactions for debugging, analytics, and cost tracking
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient
from enum import Enum

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "oemlinker")

# Gupshup pricing (approximate INR per message)
WHATSAPP_PRICING = {
    "text": {"session": 0.35, "template": 0.50},
    "image": {"session": 0.55, "template": 0.70},
    "document": {"session": 0.55, "template": 0.70},
    "audio": {"session": 0.55, "template": 0.70},
    "video": {"session": 0.85, "template": 1.00},
    "interactive": {"session": 0.45, "template": 0.60},
    "template": {"session": 0.50, "template": 0.50},
    "location": {"session": 0.35, "template": 0.50},
    "contact": {"session": 0.35, "template": 0.50},
}


class MessageDirection(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    ERROR = "error"


class WhatsAppLogger:
    """Service for logging WhatsApp interactions"""
    
    _instance = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def _get_db(self):
        """Get MongoDB database connection"""
        if self._db is None:
            client = AsyncIOMotorClient(MONGO_URL)
            self._db = client[DB_NAME]
            # Create indexes for efficient querying
            await self._db.whatsapp_logs.create_index("timestamp")
            await self._db.whatsapp_logs.create_index("phone")
            await self._db.whatsapp_logs.create_index("status")
            await self._db.whatsapp_logs.create_index("message_type")
            await self._db.whatsapp_logs.create_index("direction")
            await self._db.whatsapp_logs.create_index([("timestamp", -1)])
        return self._db
    
    async def log_outbound_message(
        self,
        phone: str,
        message_type: str,
        content: str,
        success: bool,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        template_id: Optional[str] = None,
        api_response: Optional[Dict] = None,
        vendor_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log an outbound WhatsApp message
        
        Args:
            phone: Recipient phone number
            message_type: Type of message (text, image, document, audio, template, interactive)
            content: Message content or description
            success: Whether the message was sent successfully
            message_id: Gupshup message ID
            error_message: Error message if failed
            error_code: Error code from API
            template_id: Template ID if using template
            api_response: Full API response
            vendor_id: Associated vendor ID
            user_id: Associated user ID
            context: Context/purpose (e.g., "rfq_notification", "registration", "otp")
            metadata: Additional metadata
            
        Returns:
            Log entry ID
        """
        db = await self._get_db()
        
        # Calculate estimated cost
        is_template = template_id is not None or message_type == "template"
        pricing_key = message_type if message_type in WHATSAPP_PRICING else "text"
        cost_type = "template" if is_template else "session"
        estimated_cost = WHATSAPP_PRICING.get(pricing_key, WHATSAPP_PRICING["text"]).get(cost_type, 0.35)
        
        # If message failed, no cost
        if not success:
            estimated_cost = 0
        
        log_entry = {
            "log_id": f"walog_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}",
            "direction": MessageDirection.OUTBOUND,
            "phone": phone[-10:] if len(phone) >= 10 else phone,  # Store last 10 digits
            "phone_full": phone,
            "message_type": message_type,
            "content_preview": content[:500] if content else None,  # Store preview
            "content_length": len(content) if content else 0,
            "status": MessageStatus.SENT if success else MessageStatus.FAILED,
            "success": success,
            "message_id": message_id,
            "error_message": error_message,
            "error_code": error_code,
            "template_id": template_id,
            "is_template": is_template,
            "estimated_cost_inr": estimated_cost,
            "api_response": api_response,
            "vendor_id": vendor_id,
            "user_id": user_id,
            "context": context,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "hour": datetime.now(timezone.utc).hour
        }
        
        await db.whatsapp_logs.insert_one(log_entry)
        
        if success:
            logger.info(f"WhatsApp log: {message_type} to {phone[-4:]}*** - SUCCESS (ID: {message_id})")
        else:
            logger.warning(f"WhatsApp log: {message_type} to {phone[-4:]}*** - FAILED ({error_code}: {error_message})")
        
        return log_entry["log_id"]
    
    async def log_inbound_message(
        self,
        phone: str,
        message_type: str,
        content: str,
        message_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log an inbound WhatsApp message
        
        Args:
            phone: Sender phone number
            message_type: Type of message (text, image, document, audio, button_reply)
            content: Message content
            message_id: Gupshup message ID
            vendor_id: Associated vendor ID
            user_id: Associated user ID
            metadata: Additional metadata (image_url, document_url, etc.)
            
        Returns:
            Log entry ID
        """
        db = await self._get_db()
        
        log_entry = {
            "log_id": f"walog_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}",
            "direction": MessageDirection.INBOUND,
            "phone": phone[-10:] if len(phone) >= 10 else phone,
            "phone_full": phone,
            "message_type": message_type,
            "content_preview": content[:500] if content else None,
            "content_length": len(content) if content else 0,
            "status": MessageStatus.DELIVERED,
            "success": True,
            "message_id": message_id,
            "error_message": None,
            "error_code": None,
            "template_id": None,
            "is_template": False,
            "estimated_cost_inr": 0,  # Inbound messages don't cost
            "api_response": None,
            "vendor_id": vendor_id,
            "user_id": user_id,
            "context": "inbound",
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "hour": datetime.now(timezone.utc).hour
        }
        
        await db.whatsapp_logs.insert_one(log_entry)
        
        logger.info(f"WhatsApp log: INBOUND {message_type} from {phone[-4:]}***")
        
        return log_entry["log_id"]
    
    async def update_message_status(
        self,
        message_id: str,
        status: str,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """Update status of a logged message (for delivery receipts)"""
        db = await self._get_db()
        
        update_data = {
            "status": status,
            "status_updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if error_message:
            update_data["error_message"] = error_message
        if error_code:
            update_data["error_code"] = error_code
        
        await db.whatsapp_logs.update_one(
            {"message_id": message_id},
            {"$set": update_data}
        )
    
    async def get_logs(
        self,
        direction: Optional[str] = None,
        status: Optional[str] = None,
        message_type: Optional[str] = None,
        phone: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        context: Optional[str] = None,
        errors_only: bool = False,
        limit: int = 100,
        skip: int = 0,
        sort_order: int = -1  # -1 for newest first
    ) -> Dict[str, Any]:
        """
        Get WhatsApp logs with filters
        
        Returns:
            Dict with logs list and metadata
        """
        db = await self._get_db()
        
        query = {}
        
        if direction:
            query["direction"] = direction
        
        if status:
            query["status"] = status
        
        if message_type:
            query["message_type"] = message_type
        
        if phone:
            query["phone"] = {"$regex": phone[-10:] if len(phone) >= 10 else phone}
        
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        
        if end_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_date + "T23:59:59"
            else:
                query["timestamp"] = {"$lte": end_date + "T23:59:59"}
        
        if context:
            query["context"] = context
        
        if errors_only:
            query["success"] = False
        
        # Get total count
        total = await db.whatsapp_logs.count_documents(query)
        
        # Get logs
        cursor = db.whatsapp_logs.find(query, {"_id": 0}).sort("timestamp", sort_order).skip(skip).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "skip": skip,
            "has_more": total > (skip + limit)
        }
    
    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get WhatsApp usage statistics
        
        Returns:
            Dict with various statistics
        """
        db = await self._get_db()
        
        # Build date query
        date_query = {}
        if start_date:
            date_query["timestamp"] = {"$gte": start_date}
        if end_date:
            if "timestamp" in date_query:
                date_query["timestamp"]["$lte"] = end_date + "T23:59:59"
            else:
                date_query["timestamp"] = {"$lte": end_date + "T23:59:59"}
        
        # Total messages
        total_outbound = await db.whatsapp_logs.count_documents({**date_query, "direction": "outbound"})
        total_inbound = await db.whatsapp_logs.count_documents({**date_query, "direction": "inbound"})
        
        # Success/failure counts
        success_count = await db.whatsapp_logs.count_documents({**date_query, "success": True, "direction": "outbound"})
        failure_count = await db.whatsapp_logs.count_documents({**date_query, "success": False})
        
        # Total estimated cost
        cost_pipeline = [
            {"$match": {**date_query, "direction": "outbound"}},
            {"$group": {"_id": None, "total_cost": {"$sum": "$estimated_cost_inr"}}}
        ]
        cost_result = await db.whatsapp_logs.aggregate(cost_pipeline).to_list(1)
        total_cost = cost_result[0]["total_cost"] if cost_result else 0
        
        # Message type breakdown
        type_pipeline = [
            {"$match": {**date_query, "direction": "outbound"}},
            {"$group": {"_id": "$message_type", "count": {"$sum": 1}, "cost": {"$sum": "$estimated_cost_inr"}}}
        ]
        type_result = await db.whatsapp_logs.aggregate(type_pipeline).to_list(100)
        by_type = {item["_id"]: {"count": item["count"], "cost": round(item["cost"], 2)} for item in type_result if item["_id"]}
        
        # Context breakdown
        context_pipeline = [
            {"$match": {**date_query, "direction": "outbound"}},
            {"$group": {"_id": "$context", "count": {"$sum": 1}}}
        ]
        context_result = await db.whatsapp_logs.aggregate(context_pipeline).to_list(100)
        by_context = {item["_id"]: item["count"] for item in context_result if item["_id"]}
        
        # Error breakdown
        error_pipeline = [
            {"$match": {**date_query, "success": False, "error_code": {"$ne": None}}},
            {"$group": {"_id": "$error_code", "count": {"$sum": 1}, "sample_message": {"$first": "$error_message"}}}
        ]
        error_result = await db.whatsapp_logs.aggregate(error_pipeline).to_list(100)
        errors = [{"code": item["_id"], "count": item["count"], "message": item.get("sample_message")} for item in error_result if item["_id"]]
        
        # Daily breakdown (last 7 days)
        daily_pipeline = [
            {"$match": {**date_query, "direction": "outbound"}},
            {"$group": {"_id": "$date", "count": {"$sum": 1}, "cost": {"$sum": "$estimated_cost_inr"}, "errors": {"$sum": {"$cond": ["$success", 0, 1]}}}},
            {"$sort": {"_id": -1}},
            {"$limit": 7}
        ]
        daily_result = await db.whatsapp_logs.aggregate(daily_pipeline).to_list(7)
        daily = [{"date": item["_id"], "count": item["count"], "cost": round(item["cost"], 2), "errors": item["errors"]} for item in daily_result]
        
        # Hourly distribution (last 24 hours)
        hourly_pipeline = [
            {"$match": {**date_query, "direction": "outbound"}},
            {"$group": {"_id": "$hour", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        hourly_result = await db.whatsapp_logs.aggregate(hourly_pipeline).to_list(24)
        hourly = {item["_id"]: item["count"] for item in hourly_result}
        
        # Unique recipients
        unique_recipients = len(await db.whatsapp_logs.distinct("phone", {**date_query, "direction": "outbound"}))
        
        return {
            "total_outbound": total_outbound,
            "total_inbound": total_inbound,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round((success_count / total_outbound * 100) if total_outbound > 0 else 0, 2),
            "total_estimated_cost_inr": round(total_cost, 2),
            "unique_recipients": unique_recipients,
            "by_message_type": by_type,
            "by_context": by_context,
            "top_errors": sorted(errors, key=lambda x: x["count"], reverse=True)[:10],
            "daily_breakdown": daily,
            "hourly_distribution": hourly,
            "period": {
                "start_date": start_date or "all_time",
                "end_date": end_date or "now"
            }
        }
    
    async def get_error_summary(self, days: int = 7) -> List[Dict]:
        """Get summary of errors in the last N days"""
        db = await self._get_db()
        
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        pipeline = [
            {"$match": {"success": False, "timestamp": {"$gte": start_date}}},
            {"$group": {
                "_id": {"error_code": "$error_code", "error_message": "$error_message"},
                "count": {"$sum": 1},
                "last_occurrence": {"$max": "$timestamp"},
                "sample_phone": {"$first": "$phone"},
                "sample_context": {"$first": "$context"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]
        
        results = await db.whatsapp_logs.aggregate(pipeline).to_list(20)
        
        return [
            {
                "error_code": item["_id"]["error_code"],
                "error_message": item["_id"]["error_message"],
                "count": item["count"],
                "last_occurrence": item["last_occurrence"],
                "sample_phone": f"***{item.get('sample_phone', '')[-4:]}",
                "context": item.get("sample_context")
            }
            for item in results
        ]


# Singleton instance
whatsapp_logger = WhatsAppLogger()
