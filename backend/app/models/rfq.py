"""
RFQ-related Pydantic Models
"""
from pydantic import BaseModel
from typing import List, Optional


class RFQStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ANALYZING = "analyzing"
    MATCHING = "matching"
    QUOTED = "quoted"
    PO_ISSUED = "po_issued"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SupplyType:
    VENDOR_MATERIAL = "vendor_material"
    BUYER_MATERIAL = "buyer_material"


class UrgencyLevel:
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class PaymentTerms:
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    ADVANCE_50_DELIVERY_50 = "50_advance_50_delivery"
    ADVANCE_100 = "100_advance"
    AGAINST_DELIVERY = "against_delivery"
    MILESTONE_BASED = "milestone_based"
    LETTER_OF_CREDIT = "letter_of_credit"
    CUSTOM = "custom"


class Incoterms:
    EXW = "EXW"
    FCA = "FCA"
    FAS = "FAS"
    FOB = "FOB"
    CFR = "CFR"
    CIF = "CIF"
    CPT = "CPT"
    CIP = "CIP"
    DAP = "DAP"
    DPU = "DPU"
    DDP = "DDP"


class RFQ(BaseModel):
    rfq_id: str
    buyer_id: str
    title: str
    description: Optional[str] = None
    material_type: str
    quantity: int = 1
    tolerance: float = 0.1
    surface_finish: Optional[str] = None
    supply_type: str = SupplyType.VENDOR_MATERIAL
    urgency: str = UrgencyLevel.NORMAL
    deadline: Optional[str] = None
    # Payment terms
    preferred_payment_terms: str = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None
    # Delivery location
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_country: str = "India"
    delivery_pincode: Optional[str] = None
    incoterms: str = Incoterms.EXW
    # Vendor preferences
    preferred_vendor_countries: List[str] = []
    preferred_vendor_cities: List[str] = []
    # Status and analysis
    status: str = RFQStatus.DRAFT
    ai_analysis: Optional[dict] = None
    matched_vendors: List[dict] = []
    created_at: str = ""
    updated_at: str = ""


class RFQCreate(BaseModel):
    title: str
    description: Optional[str] = None
    material_type: str
    quantity: int = 1
    tolerance: float = 0.1
    surface_finish: Optional[str] = None
    supply_type: str = SupplyType.VENDOR_MATERIAL
    urgency: str = UrgencyLevel.NORMAL
    deadline: Optional[str] = None
    # Payment terms
    preferred_payment_terms: str = PaymentTerms.NET_30
    payment_terms_notes: Optional[str] = None
    # Delivery location
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_country: str = "India"
    delivery_pincode: Optional[str] = None
    incoterms: str = Incoterms.EXW
    # Vendor preferences
    preferred_vendor_countries: List[str] = []
    preferred_vendor_cities: List[str] = []


class Drawing(BaseModel):
    drawing_id: str
    rfq_id: str
    filename: str
    file_type: str
    file_size: int
    file_data: Optional[str] = None
    analyzed: bool = False
    is_cad_attachment: bool = False
    uploaded_at: str = ""
