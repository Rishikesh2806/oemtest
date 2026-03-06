"""
Quote-related Pydantic Models
"""
from pydantic import BaseModel
from typing import Optional


class Quote(BaseModel):
    quote_id: str
    rfq_id: str
    vendor_id: str
    user_id: str
    price: float
    currency: str = "INR"
    lead_time_days: int
    notes: Optional[str] = None
    proposed_payment_terms: str = "net_30"
    payment_terms_notes: Optional[str] = None
    status: str = "pending"
    is_selected: bool = False
    negotiation_status: Optional[str] = None
    negotiation_history: list = []
    expires_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class QuoteCreate(BaseModel):
    rfq_id: str
    price: float
    lead_time_days: int
    notes: Optional[str] = None
    proposed_payment_terms: str = "net_30"
    payment_terms_notes: Optional[str] = None


class NegotiationRequest(BaseModel):
    requested_price: Optional[float] = None
    requested_lead_time: Optional[int] = None
    message: str
