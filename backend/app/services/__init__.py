"""
Services module - Business logic and data operations
"""
from app.services.user_service import (
    get_user_by_id,
    get_user_by_email,
    get_user_by_phone,
    create_user,
    update_user,
    update_user_password,
    verify_user_email,
    record_login,
)

from app.services.vendor_service import (
    get_vendor_by_user_id,
    get_vendor_by_id,
    create_vendor_profile,
    update_vendor_profile,
    get_approved_vendors,
    get_pending_vendors,
    approve_vendor,
    reject_vendor,
)

from app.services.notification_service import (
    create_notification,
    get_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    delete_notification,
)

__all__ = [
    # User service
    "get_user_by_id",
    "get_user_by_email",
    "get_user_by_phone",
    "create_user",
    "update_user",
    "update_user_password",
    "verify_user_email",
    "record_login",
    # Vendor service
    "get_vendor_by_user_id",
    "get_vendor_by_id",
    "create_vendor_profile",
    "update_vendor_profile",
    "get_approved_vendors",
    "get_pending_vendors",
    "approve_vendor",
    "reject_vendor",
    # Notification service
    "create_notification",
    "get_user_notifications",
    "mark_notification_read",
    "mark_all_notifications_read",
    "delete_notification",
]
