"""
Notification Service - Create and send notifications
"""
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.database import db


async def create_notification(
    user_id: str, 
    notification_type: str, 
    title: str, 
    message: str, 
    data: dict = None,
    send_email: bool = False,
    email_template: str = None,
    email_data: dict = None
):
    """Create an in-app notification and optionally send email"""
    now = datetime.now(timezone.utc).isoformat()
    
    notification = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "is_read": False,
        "created_at": now
    }
    
    await db.notifications.insert_one(notification)
    
    # Email sending would be handled by email_service
    # if send_email and email_template and email_data:
    #     ... (email logic)
    
    return notification


async def get_user_notifications(user_id: str, limit: int = 50, unread_only: bool = False):
    """Get notifications for a user"""
    query = {"user_id": user_id}
    if unread_only:
        query["is_read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return notifications


async def mark_notification_read(notification_id: str, user_id: str):
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": user_id},
        {"$set": {"is_read": True}}
    )
    return result.modified_count > 0


async def mark_all_notifications_read(user_id: str):
    """Mark all notifications as read for a user"""
    result = await db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return result.modified_count


async def delete_notification(notification_id: str, user_id: str):
    """Delete a notification"""
    result = await db.notifications.delete_one(
        {"notification_id": notification_id, "user_id": user_id}
    )
    return result.deleted_count > 0
