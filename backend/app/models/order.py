"""
Order-related Pydantic Models
"""
from pydantic import BaseModel
from typing import Optional


class OrderStatus:
    CREATED = "created"
    CONFIRMED = "confirmed"
    IN_PRODUCTION = "in_production"
    QUALITY_CHECK = "quality_check"
    READY_TO_SHIP = "ready_to_ship"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(BaseModel):
    order_id: str
    rfq_id: str
    quote_id: str
    buyer_id: str
    vendor_id: str
    status: str = OrderStatus.CREATED
    total_amount: float
    currency: str = "INR"
    payment_terms: str = "net_30"
    payment_status: str = "pending"
    expected_delivery: Optional[str] = None
    actual_delivery: Optional[str] = None
    shipping_address: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
