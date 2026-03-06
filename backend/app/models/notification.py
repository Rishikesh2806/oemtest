"""
Notification-related Pydantic Models
"""


class NotificationType:
    RFQ_CREATED = "rfq_created"
    RFQ_MATCHED = "rfq_matched"
    QUOTE_RECEIVED = "quote_received"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    MESSAGE_RECEIVED = "message_received"
    VENDOR_APPROVED = "vendor_approved"
    VENDOR_REJECTED = "vendor_rejected"
    NEGOTIATION_REQUEST = "negotiation_request"
    NEGOTIATION_RESPONSE = "negotiation_response"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_DUE = "payment_due"
    RATING_RECEIVED = "rating_received"
    SYSTEM = "system"
