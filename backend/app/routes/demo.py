"""
Demo Routes - Seed demo data and provide demo login
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
import uuid
import bcrypt
import jwt
import os
import logging

from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo"])

JWT_SECRET = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"

DEMO_PASSWORD = "demo123"
DEMO_BUYER_EMAIL = "demo.buyer@oemlinker.com"
DEMO_VENDOR_EMAIL = "demo.vendor@oemlinker.com"
DEMO_ADMIN_EMAIL = "admin@offoadex.com"


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def make_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@router.post("/seed")
async def seed_demo_data():
    """Seed realistic demo data for buyer, vendor, and admin walkthrough"""
    now = datetime.now(timezone.utc).isoformat()
    one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    # ── Demo Buyer ──
    buyer_id = "user_demo_buyer_001"
    existing_buyer = await db.users.find_one({"user_id": buyer_id})
    if not existing_buyer:
        await db.users.insert_one({
            "user_id": buyer_id,
            "email": DEMO_BUYER_EMAIL,
            "name": "Rajesh Kumar",
            "password_hash": hash_pw(DEMO_PASSWORD),
            "role": "buyer",
            "company_name": "Precision Auto Components Pvt Ltd",
            "email_verified": True,
            "phone_number": "+91 98765 12345",
            "created_at": one_week_ago
        })

    # ── Demo Vendor 1 (Primary) ──
    vendor_user_id = "user_demo_vendor_001"
    vendor_id = "vendor_demo_001"
    existing_vendor = await db.users.find_one({"user_id": vendor_user_id})
    if not existing_vendor:
        await db.users.insert_one({
            "user_id": vendor_user_id,
            "email": DEMO_VENDOR_EMAIL,
            "name": "Suresh Patel",
            "password_hash": hash_pw(DEMO_PASSWORD),
            "role": "vendor",
            "company_name": "Patel Precision Engineering",
            "email_verified": True,
            "phone_number": "+91 99887 54321",
            "created_at": one_week_ago
        })

    existing_vp = await db.vendors.find_one({"vendor_id": vendor_id})
    if not existing_vp:
        await db.vendors.insert_one({
            "vendor_id": vendor_id,
            "user_id": vendor_user_id,
            "company_name": "Patel Precision Engineering",
            "description": "ISO 9001:2015 certified precision machining facility with 20+ years of experience in CNC machining, turning, milling, and grinding. We serve aerospace, automotive, and defense industries.",
            "gstin": "24AABCP1234M1ZX",
            "gst_verified": True,
            "gst_status": "Active",
            "legal_name": "Patel Precision Engineering Pvt Ltd",
            "trade_name": "Patel Precision",
            "taxpayer_type": "Regular",
            "constitution": "Private Limited Company",
            "gst_registration_date": "2010-06-15",
            "address": "Plot 45, GIDC Industrial Estate, Phase 2",
            "city": "Ahmedabad",
            "state": "Gujarat",
            "pincode": "382445",
            "country": "India",
            "phone": "+91 99887 54321",
            "contact_email": DEMO_VENDOR_EMAIL,
            "website": "https://patelprecision.example.com",
            "certifications": ["ISO 9001:2015", "ISO 14001", "AS9100D", "IATF 16949"],
            "industries": ["Aerospace", "Automotive", "Defense", "Medical Devices"],
            "materials_handled": ["Mild Steel", "Stainless Steel", "Aluminium", "Titanium", "Inconel", "Brass"],
            "is_approved": True,
            "rating": 4.7,
            "total_jobs": 156,
            "past_experiences": [
                {"title": "Aerospace Landing Gear Components", "description": "Precision machined titanium landing gear fittings for a major aircraft OEM. Tolerance of +/-0.005mm achieved.", "industry": "Aerospace", "material": "Titanium Ti-6Al-4V", "processes_used": ["CNC Milling", "CNC Turning", "Surface Grinding"], "part_type": "Structural Fitting", "year": 2024},
                {"title": "Automotive Transmission Shaft", "description": "High-volume production of hardened steel transmission shafts with spline cutting.", "industry": "Automotive", "material": "EN24 Steel", "processes_used": ["CNC Turning", "Gear Hobbing", "Heat Treatment"], "part_type": "Shaft", "year": 2025},
                {"title": "Medical Implant Housings", "description": "Micro-machined stainless steel housings for surgical instruments with mirror finish.", "industry": "Medical Devices", "material": "SS 316L", "processes_used": ["CNC Milling", "EDM", "Polishing"], "part_type": "Housing", "year": 2025}
            ],
            "created_at": one_week_ago
        })

    # ── Demo Vendor 2 (Secondary for comparison) ──
    vendor2_user_id = "user_demo_vendor_002"
    vendor2_id = "vendor_demo_002"
    existing_v2 = await db.users.find_one({"user_id": vendor2_user_id})
    if not existing_v2:
        await db.users.insert_one({
            "user_id": vendor2_user_id,
            "email": "demo.vendor2@oemlinker.com",
            "name": "Anil Sharma",
            "password_hash": hash_pw(DEMO_PASSWORD),
            "role": "vendor",
            "company_name": "Sharma Machine Works",
            "email_verified": True,
            "created_at": one_week_ago
        })

    existing_vp2 = await db.vendors.find_one({"vendor_id": vendor2_id})
    if not existing_vp2:
        await db.vendors.insert_one({
            "vendor_id": vendor2_id,
            "user_id": vendor2_user_id,
            "company_name": "Sharma Machine Works",
            "description": "Specialized in sheet metal fabrication and CNC machining with quick turnaround times. Expert in prototyping and small-batch production.",
            "address": "B-12, Sector 63, Noida Industrial Area",
            "city": "Noida",
            "state": "Uttar Pradesh",
            "pincode": "201301",
            "country": "India",
            "certifications": ["ISO 9001:2015"],
            "industries": ["Automotive", "Electronics", "General Engineering"],
            "materials_handled": ["Mild Steel", "Aluminium", "Brass", "Copper"],
            "is_approved": True,
            "rating": 4.2,
            "total_jobs": 89,
            "past_experiences": [
                {"title": "Electronic Enclosures", "description": "Sheet metal enclosures for IoT devices with powder coating finish.", "industry": "Electronics", "material": "Aluminium 6061", "processes_used": ["Sheet Metal Cutting", "CNC Bending", "Powder Coating"], "part_type": "Enclosure", "year": 2025}
            ],
            "created_at": one_week_ago
        })

    # ── Machines for Vendor 1 ──
    machines_v1 = [
        {
            "machine_id": "mach_demo_001",
            "vendor_id": vendor_id,
            "name": "Mazak Integrex i-200S",
            "machine_category": "CNC Turning",
            "machine_type": "CNC Lathe",
            "brand": "Mazak",
            "model": "Integrex i-200S",
            "max_diameter": 660,
            "max_length": 1524,
            "max_swing": 700,
            "tolerance": 0.005,
            "tolerance_capability": 0.005,
            "materials_supported": ["Mild Steel", "Stainless Steel", "Aluminium", "Titanium", "Inconel"],
            "monthly_capacity_hours": 480,
            "is_active": True,
            "has_complete_specs": True,
            "availability_status": "available",
            "created_at": one_week_ago
        },
        {
            "machine_id": "mach_demo_002",
            "vendor_id": vendor_id,
            "name": "DMG Mori DMU 50 3rd Gen",
            "machine_category": "CNC Milling",
            "machine_type": "5-Axis VMC",
            "brand": "DMG Mori",
            "model": "DMU 50 3rd Gen",
            "max_x": 500,
            "max_y": 450,
            "max_z": 400,
            "tolerance": 0.003,
            "tolerance_capability": 0.003,
            "a_axis_range": 180,
            "c_axis_range": 360,
            "materials_supported": ["Stainless Steel", "Aluminium", "Titanium", "Inconel", "Tool Steel"],
            "monthly_capacity_hours": 480,
            "is_active": True,
            "has_complete_specs": True,
            "availability_status": "available",
            "created_at": one_week_ago
        },
        {
            "machine_id": "mach_demo_003",
            "vendor_id": vendor_id,
            "name": "Okuma GENOS M560-V",
            "machine_category": "CNC Milling",
            "machine_type": "VMC",
            "brand": "Okuma",
            "model": "GENOS M560-V",
            "max_x": 1050,
            "max_y": 560,
            "max_z": 460,
            "tolerance": 0.01,
            "tolerance_capability": 0.01,
            "materials_supported": ["Mild Steel", "Stainless Steel", "Aluminium", "Brass", "Cast Iron"],
            "monthly_capacity_hours": 320,
            "is_active": True,
            "has_complete_specs": True,
            "availability_status": "available",
            "created_at": one_week_ago
        }
    ]

    for m in machines_v1:
        existing_m = await db.machines.find_one({"machine_id": m["machine_id"]})
        if not existing_m:
            await db.machines.insert_one(m)

    # ── Machines for Vendor 2 ──
    machines_v2 = [
        {
            "machine_id": "mach_demo_004",
            "vendor_id": vendor2_id,
            "name": "Haas VF-2SS",
            "machine_category": "CNC Milling",
            "machine_type": "VMC",
            "brand": "Haas",
            "model": "VF-2SS",
            "max_x": 762,
            "max_y": 406,
            "max_z": 508,
            "tolerance": 0.02,
            "tolerance_capability": 0.02,
            "materials_supported": ["Mild Steel", "Aluminium", "Brass", "Copper"],
            "monthly_capacity_hours": 320,
            "is_active": True,
            "has_complete_specs": True,
            "availability_status": "available",
            "created_at": one_week_ago
        }
    ]

    for m in machines_v2:
        existing_m = await db.machines.find_one({"machine_id": m["machine_id"]})
        if not existing_m:
            await db.machines.insert_one(m)

    # ── Demo RFQs ──
    rfqs = [
        {
            "rfq_id": "rfq_demo_001",
            "ref_number": "RFQ-2026-0001",
            "title": "Aerospace Bracket - Titanium Ti-6Al-4V",
            "description": "Precision machined aerospace bracket for landing gear assembly. Material: Titanium Ti-6Al-4V, Grade 5. Requires 5-axis CNC milling with tight tolerances. Surface finish Ra 0.8um. Quantity: 50 pieces. Delivery needed within 4 weeks.",
            "buyer_id": buyer_id,
            "buyer_name": "Rajesh Kumar",
            "buyer_company": "Precision Auto Components Pvt Ltd",
            "material_type": "Titanium",
            "quantity": 50,
            "tolerance": 0.005,
            "status": "quoted",
            "image_type": "technical_drawing",
            "ai_analysis": {
                "image_type": "technical_drawing",
                "part_geometry": "complex",
                "overall_dimensions": {"length": 180, "width": 95, "height": 45, "unit": "mm"},
                "critical_tolerances": [
                    {"feature": "Bore holes", "tolerance": 0.005, "unit": "mm"},
                    {"feature": "Mounting surface", "tolerance": 0.01, "unit": "mm"}
                ],
                "recommended_processes": ["5-Axis CNC Milling", "CNC Drilling", "Deburring", "Anodizing"],
                "material_detected": "Titanium Ti-6Al-4V",
                "surface_finish": "Ra 0.8",
                "complexity_score": 8
            },
            "matched_vendors": [
                {
                    "vendor_id": vendor_id,
                    "company_name": "Patel Precision Engineering",
                    "match_score": 92,
                    "validation_category": "capable",
                    "matching_machines": [{"machine_id": "mach_demo_002", "name": "DMG Mori DMU 50 3rd Gen", "machine_type": "5-Axis VMC"}],
                    "tolerance_capable": True,
                    "material_capable": True,
                    "city": "Ahmedabad",
                    "state": "Gujarat"
                },
                {
                    "vendor_id": vendor2_id,
                    "company_name": "Sharma Machine Works",
                    "match_score": 61,
                    "validation_category": "unverified",
                    "matching_machines": [{"machine_id": "mach_demo_004", "name": "Haas VF-2SS", "machine_type": "VMC"}],
                    "tolerance_capable": False,
                    "material_capable": False,
                    "city": "Noida",
                    "state": "Uttar Pradesh"
                }
            ],
            "created_at": three_days_ago,
            "updated_at": yesterday
        },
        {
            "rfq_id": "rfq_demo_002",
            "ref_number": "RFQ-2026-0002",
            "title": "CNC Turned Shaft - EN24 Steel",
            "description": "High-precision turned shaft for automotive gearbox. EN24 steel, hardened to 58-62 HRC. Spline cutting required. Quantity: 500 pieces/month for 12 months.",
            "buyer_id": buyer_id,
            "buyer_name": "Rajesh Kumar",
            "buyer_company": "Precision Auto Components Pvt Ltd",
            "material_type": "EN24 Steel",
            "quantity": 500,
            "tolerance": 0.01,
            "status": "matching",
            "image_type": "technical_drawing",
            "ai_analysis": {
                "image_type": "technical_drawing",
                "part_geometry": "cylindrical",
                "overall_dimensions": {"diameter": 45, "length": 320, "unit": "mm"},
                "critical_tolerances": [
                    {"feature": "Journal diameter", "tolerance": 0.01, "unit": "mm"},
                    {"feature": "Spline pitch", "tolerance": 0.02, "unit": "mm"}
                ],
                "recommended_processes": ["CNC Turning", "Spline Cutting", "Heat Treatment", "Cylindrical Grinding"],
                "material_detected": "EN24 Steel",
                "complexity_score": 6
            },
            "matched_vendors": [
                {
                    "vendor_id": vendor_id,
                    "company_name": "Patel Precision Engineering",
                    "match_score": 95,
                    "validation_category": "capable",
                    "matching_machines": [{"machine_id": "mach_demo_001", "name": "Mazak Integrex i-200S", "machine_type": "CNC Lathe"}],
                    "tolerance_capable": True,
                    "material_capable": True,
                    "city": "Ahmedabad",
                    "state": "Gujarat"
                }
            ],
            "created_at": yesterday,
            "updated_at": yesterday
        },
        {
            "rfq_id": "rfq_demo_003",
            "ref_number": "RFQ-2026-0003",
            "title": "Aluminium Housing - Die Cast Prototype",
            "description": "Prototype CNC machined housing from Aluminium 6061-T6. For electronic controller enclosure. Need 5 samples for testing.",
            "buyer_id": buyer_id,
            "buyer_name": "Rajesh Kumar",
            "buyer_company": "Precision Auto Components Pvt Ltd",
            "material_type": "Aluminium 6061",
            "quantity": 5,
            "tolerance": 0.05,
            "status": "draft",
            "image_type": "reference_photo",
            "created_at": now,
            "updated_at": now
        }
    ]

    for rfq in rfqs:
        await db.rfqs.update_one(
            {"rfq_id": rfq["rfq_id"]},
            {"$set": rfq},
            upsert=True
        )

    # ── Demo Quotes ──
    quotes = [
        {
            "quote_id": "quote_demo_001",
            "rfq_id": "rfq_demo_001",
            "vendor_id": vendor_id,
            "vendor_name": "Patel Precision Engineering",
            "buyer_id": buyer_id,
            "status": "submitted",
            "items": [
                {
                    "description": "Aerospace Bracket - Titanium Ti-6Al-4V",
                    "quantity": 50,
                    "unit_price": 4500,
                    "total_price": 225000,
                    "lead_time_days": 21,
                    "notes": "Price includes 5-axis machining, deburring, and material certification. Can start production within 3 days of PO."
                }
            ],
            "total_amount": 225000,
            "currency": "INR",
            "validity_days": 30,
            "lead_time_days": 21,
            "payment_terms": "50% advance, 50% on delivery",
            "notes": "We have extensive experience with Ti-6Al-4V machining for aerospace applications. All parts will come with material test certificates and dimensional inspection reports.",
            "created_at": yesterday,
            "updated_at": yesterday
        },
        {
            "quote_id": "quote_demo_002",
            "rfq_id": "rfq_demo_001",
            "vendor_id": vendor2_id,
            "vendor_name": "Sharma Machine Works",
            "buyer_id": buyer_id,
            "status": "submitted",
            "items": [
                {
                    "description": "Aerospace Bracket - Titanium Ti-6Al-4V",
                    "quantity": 50,
                    "unit_price": 5200,
                    "total_price": 260000,
                    "lead_time_days": 28,
                    "notes": "Price includes machining and basic finishing. Material to be sourced from approved supplier."
                }
            ],
            "total_amount": 260000,
            "currency": "INR",
            "validity_days": 15,
            "lead_time_days": 28,
            "payment_terms": "100% advance",
            "notes": "We can handle this job on our Haas VF-2SS. Lead time includes material procurement.",
            "created_at": yesterday,
            "updated_at": yesterday
        }
    ]

    for q in quotes:
        existing_q = await db.quotes.find_one({"quote_id": q["quote_id"]})
        if not existing_q:
            await db.quotes.insert_one(q)

    # ── Demo Order (for showing order tracking) ──
    order = {
        "order_id": "order_demo_001",
        "ref_number": "ORD-2026-0001",
        "rfq_id": "rfq_demo_001",
        "quote_id": "quote_demo_001",
        "buyer_id": buyer_id,
        "vendor_id": vendor_id,
        "buyer_name": "Rajesh Kumar",
        "vendor_name": "Patel Precision Engineering",
        "status": "in_production",
        "total_amount": 225000,
        "currency": "INR",
        "items": [{"description": "Aerospace Bracket - Titanium Ti-6Al-4V", "quantity": 50, "unit_price": 4500}],
        "payment_status": "partial_paid",
        "created_at": yesterday,
        "updated_at": now
    }
    existing_order = await db.orders.find_one({"order_id": order["order_id"]})
    if not existing_order:
        await db.orders.insert_one(order)

    return {
        "message": "Demo data seeded successfully",
        "accounts": {
            "buyer": {"email": DEMO_BUYER_EMAIL, "password": DEMO_PASSWORD, "name": "Rajesh Kumar"},
            "vendor": {"email": DEMO_VENDOR_EMAIL, "password": DEMO_PASSWORD, "name": "Suresh Patel"},
            "admin": {"email": DEMO_ADMIN_EMAIL, "password": "admin123", "name": "Admin User"}
        }
    }


@router.post("/login")
async def demo_login(request_data: dict):
    """Quick login for demo accounts"""
    role = request_data.get("role", "buyer")
    
    email_map = {
        "buyer": DEMO_BUYER_EMAIL,
        "vendor": DEMO_VENDOR_EMAIL,
        "admin": DEMO_ADMIN_EMAIL
    }
    
    email = email_map.get(role)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid demo role")
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail=f"Demo {role} account not found. Please seed demo data first.")
    
    token = make_token(user["user_id"], user["email"], user["role"])
    
    return {
        "access_token": token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "company_name": user.get("company_name", ""),
        }
    }


DEMO_USER_IDS = ["user_demo_buyer_001", "user_demo_vendor_001", "user_demo_vendor_002"]
DEMO_VENDOR_IDS = ["vendor_demo_001", "vendor_demo_002"]
DEMO_MACHINE_IDS = ["mach_demo_001", "mach_demo_002", "mach_demo_003", "mach_demo_004"]


def is_demo_user(user_id: str) -> bool:
    """Check if a user_id belongs to a demo account"""
    return user_id in DEMO_USER_IDS


@router.post("/cleanup")
async def cleanup_demo_data():
    """Delete ALL data created by demo users — RFQs, orders, quotes, machines, vendor profiles, users"""
    results = {}

    # Delete ALL orders involving demo users (as buyer or vendor)
    r = await db.orders.delete_many({
        "$or": [
            {"buyer_id": {"$in": DEMO_USER_IDS}},
            {"vendor_id": {"$in": DEMO_VENDOR_IDS}}
        ]
    })
    results["orders_deleted"] = r.deleted_count

    # Delete ALL quotes involving demo users
    r = await db.quotes.delete_many({
        "$or": [
            {"buyer_id": {"$in": DEMO_USER_IDS}},
            {"vendor_id": {"$in": DEMO_VENDOR_IDS}}
        ]
    })
    results["quotes_deleted"] = r.deleted_count

    # Delete ALL RFQs created by demo buyer
    r = await db.rfqs.delete_many({"buyer_id": {"$in": DEMO_USER_IDS}})
    results["rfqs_deleted"] = r.deleted_count

    # Delete demo machines
    r = await db.machines.delete_many({"machine_id": {"$in": DEMO_MACHINE_IDS}})
    results["machines_deleted"] = r.deleted_count

    # Delete demo vendor profiles
    r = await db.vendors.delete_many({"vendor_id": {"$in": DEMO_VENDOR_IDS}})
    results["vendor_profiles_deleted"] = r.deleted_count

    # Delete demo users (buyer + vendors, NOT admin)
    r = await db.users.delete_many({"user_id": {"$in": DEMO_USER_IDS}})
    results["users_deleted"] = r.deleted_count

    # Delete any NDA acceptances by demo vendors
    r = await db.nda_acceptances.delete_many({"vendor_id": {"$in": DEMO_VENDOR_IDS}})
    results["nda_acceptances_deleted"] = r.deleted_count

    logger.info(f"Demo cleanup complete: {results}")
    return {"message": "Demo data cleaned up", "details": results}
