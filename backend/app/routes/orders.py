"""
Order Routes - Order management for buyers, vendors, and admins
- Order listing (buyer/vendor specific)
- Order status updates
- Order details
- Rating system
- Delivery confirmation
- Tracking
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from app.database import db
from app.routes.auth import get_current_user
from app.models.base import UserRole, OrderStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Orders"])


# ============== BUYER ORDER ROUTES ==============

@router.get("/buyer/orders")
async def list_buyer_orders(user: dict = Depends(get_current_user)):
    """List all orders for the authenticated buyer"""
    if user.get("role") != UserRole.BUYER and user.get("role") != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can access this endpoint")
    
    orders = await db.orders.find({"buyer_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Enrich orders with vendor info and RFQ title
    enriched_orders = []
    for order in orders:
        # Get vendor info
        vendor = await db.vendors.find_one({"vendor_id": order.get("vendor_id")}, {"_id": 0, "company_name": 1})
        order["vendor_name"] = vendor.get("company_name") if vendor else None
        
        # Get RFQ title
        rfq = await db.rfqs.find_one({"rfq_id": order.get("rfq_id")}, {"_id": 0, "title": 1})
        order["rfq_title"] = rfq.get("title") if rfq else None
        
        enriched_orders.append(order)
    
    return {"orders": enriched_orders, "total": len(enriched_orders)}


# ============== VENDOR ORDER ROUTES ==============

@router.get("/vendor/orders")
async def list_vendor_orders(user: dict = Depends(get_current_user)):
    """List all orders for the authenticated vendor"""
    user_role = user.get("role", "")
    
    # Check if user is a vendor (by role or has vendor profile)
    vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not vendor:
        return {"orders": [], "total": 0}
    
    orders = await db.orders.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Enrich orders with buyer info and RFQ title
    enriched_orders = []
    for order in orders:
        # Get buyer info
        buyer = await db.users.find_one({"user_id": order.get("buyer_id")}, {"_id": 0, "name": 1, "company": 1})
        order["buyer_name"] = buyer.get("company") or buyer.get("name") if buyer else None
        
        # Get RFQ title
        rfq = await db.rfqs.find_one({"rfq_id": order.get("rfq_id")}, {"_id": 0, "title": 1})
        order["rfq_title"] = rfq.get("title") if rfq else None
        
        enriched_orders.append(order)
    
    return {"orders": enriched_orders, "total": len(enriched_orders)}


# ============== GENERAL ORDER ROUTES ==============

@router.get("/orders")
async def list_orders(user: dict = Depends(get_current_user)):
    """List orders based on user role"""
    user_role = user.get("role", "")
    
    if user_role in ["admin", "staff", UserRole.ADMIN]:
        # Admins can see all orders
        orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    elif user_role in ["buyer", UserRole.BUYER]:
        # Buyers see their orders
        orders = await db.orders.find({"buyer_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    else:
        # Vendors see orders assigned to them
        vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if vendor:
            orders = await db.orders.find({"vendor_id": vendor["vendor_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
        else:
            orders = []
    
    return orders


@router.get("/orders/{order_id}")
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    """Get order by ID"""
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update order status with payment gate enforcement"""
    body = await request.json()
    new_status = body.get("status")
    note = body.get("note", "")
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Payment gate enforcement
    admin_override = body.get("admin_override", False)
    is_admin = user.get("role") == "admin"
    schedule = order.get("payment_schedule")
    
    STAGE_GATE = {
        "before_production": "in_production",
        "after_production": "quality_check",
        "after_inspection": "dispatched",
        "after_dispatch": "delivered",
        "on_delivery": "completed",
    }
    
    if schedule and not (admin_override and is_admin):
        for ms in schedule.get("milestones", []):
            if ms.get("status") == "pending":
                gate_target = STAGE_GATE.get(ms.get("stage"))
                if gate_target and gate_target == new_status:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Payment required: '{ms.get('label', ms['stage'])}' "
                               f"({ms['percentage']}% = {order.get('currency', 'INR')} "
                               f"{ms['amount']:,.2f}) must be paid before moving to {new_status.replace('_', ' ')}"
                    )
    
    # Update order status
    update_data = {
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add status-specific timestamps
    if new_status == OrderStatus.SHIPPED:
        update_data["shipped_at"] = datetime.now(timezone.utc).isoformat()
    elif new_status == OrderStatus.DELIVERED:
        update_data["delivered_at"] = datetime.now(timezone.utc).isoformat()
    elif new_status == OrderStatus.COMPLETED:
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    # Add status history entry
    history_entry = {
        "status": new_status,
        "note": note,
        "changed_by": user["user_id"],
        "changed_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$set": update_data,
            "$push": {"status_history": history_entry}
        }
    )
    
    logger.info(f"Order {order_id} status updated to {new_status} by {user['user_id']}")
    
    return {"message": "Order status updated", "status": new_status}


@router.get("/orders/{order_id}/details")
async def get_order_details(order_id: str, user: dict = Depends(get_current_user)):
    """Get detailed order information including related entities"""
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get quote details
    quote = await db.quotes.find_one({"quote_id": order.get("quote_id")}, {"_id": 0})
    
    # Get RFQ details
    rfq = await db.rfqs.find_one({"rfq_id": order.get("rfq_id")}, {"_id": 0})
    
    # Get vendor details
    vendor = await db.vendors.find_one({"vendor_id": order.get("vendor_id")}, {"_id": 0})
    
    # Get buyer details
    buyer = await db.users.find_one({"user_id": order.get("buyer_id")}, {"_id": 0, "password_hash": 0})
    
    # Get inspection if exists
    inspection = await db.inspections.find_one({"order_id": order_id}, {"_id": 0})
    
    return {
        "order": order,
        "quote": quote,
        "rfq": rfq,
        "vendor": vendor,
        "buyer": buyer,
        "inspection": inspection
    }


# ============== RATING ROUTES ==============

@router.post("/orders/{order_id}/rate")
async def rate_order(order_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Submit rating for a completed order"""
    body = await request.json()
    rating = body.get("rating")
    review = body.get("review", "")
    
    if not rating or rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only completed orders can be rated
    if order.get("status") not in ["delivered", "completed"]:
        raise HTTPException(status_code=400, detail="Only completed orders can be rated")
    
    # Create rating record
    rating_doc = {
        "rating_id": f"rating_{uuid.uuid4().hex[:12]}",
        "order_id": order_id,
        "rfq_id": order.get("rfq_id"),
        "vendor_id": order.get("vendor_id"),
        "buyer_id": user["user_id"],
        "rating": rating,
        "review": review,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ratings.insert_one(rating_doc)
    
    # Update vendor's average rating
    vendor_ratings = await db.ratings.find({"vendor_id": order.get("vendor_id")}).to_list(1000)
    if vendor_ratings:
        avg_rating = sum(r.get("rating", 0) for r in vendor_ratings) / len(vendor_ratings)
        await db.vendors.update_one(
            {"vendor_id": order.get("vendor_id")},
            {"$set": {"rating": round(avg_rating, 2), "total_jobs": len(vendor_ratings)}}
        )
    
    # Update order with rating reference
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"rating_id": rating_doc["rating_id"], "rated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    logger.info(f"Order {order_id} rated {rating}/5 by buyer {user['user_id']}")
    
    return {"message": "Rating submitted successfully", "rating": rating_doc}


@router.get("/orders/{order_id}/rating")
async def get_order_rating(order_id: str, user: dict = Depends(get_current_user)):
    """Get rating for an order"""
    rating = await db.ratings.find_one({"order_id": order_id}, {"_id": 0})
    if not rating:
        return {"rating": None}
    return {"rating": rating}


# ============== DELIVERY & TRACKING ==============

@router.post("/orders/{order_id}/confirm-delivery")
async def confirm_delivery(order_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Buyer confirms delivery of order"""
    body = await request.json()
    notes = body.get("notes", "")
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only buyer can confirm delivery
    if order.get("buyer_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the buyer can confirm delivery")
    
    update_data = {
        "status": OrderStatus.DELIVERED,
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "delivery_confirmed_by": user["user_id"],
        "delivery_notes": notes,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.orders.update_one({"order_id": order_id}, {"$set": update_data})
    
    logger.info(f"Delivery confirmed for order {order_id} by buyer {user['user_id']}")
    
    return {"message": "Delivery confirmed successfully", "status": OrderStatus.DELIVERED}


@router.post("/orders/{order_id}/add-tracking")
async def add_tracking(order_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Add tracking information to order"""
    body = await request.json()
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    tracking_info = {
        "tracking_number": body.get("tracking_number"),
        "carrier": body.get("carrier"),
        "tracking_url": body.get("tracking_url"),
        "estimated_delivery": body.get("estimated_delivery"),
        "added_at": datetime.now(timezone.utc).isoformat(),
        "added_by": user["user_id"]
    }
    
    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$set": {"tracking": tracking_info, "updated_at": datetime.now(timezone.utc).isoformat()},
            "$push": {"tracking_history": tracking_info}
        }
    )
    
    logger.info(f"Tracking info added to order {order_id}")
    
    return {"message": "Tracking information added", "tracking": tracking_info}
