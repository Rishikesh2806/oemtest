"""
Email Service - Handles all email operations using Resend
"""
import logging
import asyncio
import resend
from app.config import RESEND_API_KEY, APP_URL, ADMIN_EMAIL

logger = logging.getLogger(__name__)

# Initialize Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

SENDER_EMAIL = "OEMLinker <notifications@oemlinker.com>"


async def send_email_async(to_email: str, subject: str, html_content: str):
    """Send email asynchronously using Resend"""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return None
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return None


async def send_admin_notification(event_type: str, data: dict):
    """Send notification email to admin for important platform events"""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured, skipping admin notification")
        return None
    
    templates = {
        "new_user": {
            "subject": f"New User Registration: {data.get('name', 'Unknown')}",
            "html": _get_admin_template("new_user", data)
        },
        "new_rfq": {
            "subject": f"New RFQ Created: {data.get('title', 'Untitled')}",
            "html": _get_admin_template("new_rfq", data)
        },
        "new_quotation": {
            "subject": f"New Quotation: Rs.{data.get('total_amount', 0):,.2f}",
            "html": _get_admin_template("new_quotation", data)
        },
        "vendor_matching": {
            "subject": f"Vendor Matching: {data.get('matched_count', 0)} vendors",
            "html": _get_admin_template("vendor_matching", data)
        },
        "quotation_accepted": {
            "subject": f"Quotation Accepted: PO #{data.get('po_number', 'N/A')}",
            "html": _get_admin_template("quotation_accepted", data)
        },
        "new_po": {
            "subject": f"New Purchase Order: PO #{data.get('po_number', 'N/A')}",
            "html": _get_admin_template("new_po", data)
        }
    }
    
    template = templates.get(event_type)
    if not template:
        logger.warning(f"Unknown admin notification type: {event_type}")
        return None
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"[OEMLinker Admin] {template['subject']}",
            "html": template["html"]
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Admin notification sent for {event_type}: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to send admin notification for {event_type}: {str(e)}")
        return None


async def send_verification_email(email: str, name: str, verification_token: str):
    """Send email verification link"""
    verification_url = f"{APP_URL}/verify-email?token={verification_token}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">OEMLinker</h1>
            <p style="color: #94a3b8; margin-top: 5px;">Verify Your Email</p>
        </div>
        <div style="padding: 30px; background: #f8fafc;">
            <h2 style="color: #1e3a5f; margin-top: 0;">Hello {name},</h2>
            <p style="color: #475569; font-size: 16px; line-height: 1.6;">
                Thank you for registering with OEMLinker. Please verify your email address 
                to complete your registration and access all features.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background: linear-gradient(135deg, #059669 0%, #047857 100%); 
                          color: white; padding: 14px 35px; text-decoration: none; 
                          border-radius: 8px; font-weight: bold; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p style="color: #64748b; font-size: 14px;">
                If you didn't create an account, you can safely ignore this email.
            </p>
            <p style="color: #64748b; font-size: 14px;">
                This link will expire in 24 hours.
            </p>
        </div>
        <div style="background: #1e293b; padding: 20px; text-align: center;">
            <p style="color: #94a3b8; margin: 0; font-size: 12px;">
                OEMLinker - AI-Powered Manufacturing Marketplace
            </p>
        </div>
    </div>
    """
    
    return await send_email_async(email, "Verify Your Email - OEMLinker", html_content)


def _get_admin_template(template_type: str, data: dict) -> str:
    """Generate HTML template for admin notifications"""
    base_style = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, {color1} 0%, {color2} 100%); padding: 20px; text-align: center;">
            <h2 style="color: white; margin: 0;">{title}</h2>
        </div>
        <div style="padding: 25px; background: #f8fafc;">
            <p style="font-size: 16px; color: #334155;"><strong>{description}</strong></p>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                {rows}
            </table>
        </div>
    </div>
    """
    
    row_template = '<tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">{label}:</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0;{style}">{value}</td></tr>'
    
    templates = {
        "new_user": {
            "color1": "#1e3a5f", "color2": "#2d5a87",
            "title": "New User Registration",
            "description": "A new user has registered on OEMLinker:",
            "rows": [
                ("Name", data.get('name', 'N/A'), " font-weight: bold;"),
                ("Email", data.get('email', 'N/A'), ""),
                ("Role", data.get('role', 'N/A').upper(), ""),
                ("Company", data.get('company_name', 'N/A'), ""),
                ("Registered At", data.get('created_at', 'N/A'), "")
            ]
        },
        "new_rfq": {
            "color1": "#059669", "color2": "#047857",
            "title": "New RFQ Created",
            "description": "A new RFQ has been submitted:",
            "rows": [
                ("RFQ ID", data.get('rfq_id', 'N/A'), " font-family: monospace;"),
                ("Title", data.get('title', 'N/A'), " font-weight: bold;"),
                ("Buyer", f"{data.get('buyer_name', 'N/A')} ({data.get('buyer_email', 'N/A')})", ""),
                ("Material", data.get('material_type', 'N/A'), ""),
                ("Quantity", str(data.get('quantity', 'N/A')), ""),
                ("Created At", data.get('created_at', 'N/A'), "")
            ]
        },
        "new_quotation": {
            "color1": "#7c3aed", "color2": "#6d28d9",
            "title": "New Quotation Submitted",
            "description": "A vendor has submitted a quotation:",
            "rows": [
                ("Quote ID", data.get('quote_id', 'N/A'), " font-family: monospace;"),
                ("RFQ Title", data.get('rfq_title', 'N/A'), ""),
                ("Vendor", data.get('vendor_name', 'N/A'), ""),
                ("Buyer", data.get('buyer_name', 'N/A'), ""),
                ("Amount", f"Rs.{data.get('total_amount', 0):,.2f}", " font-weight: bold; color: #059669;"),
                ("Lead Time", f"{data.get('lead_time', 'N/A')} days", "")
            ]
        },
        "vendor_matching": {
            "color1": "#f97316", "color2": "#ea580c",
            "title": "Vendor Matching Complete",
            "description": "AI matching has found suitable vendors:",
            "rows": [
                ("RFQ ID", data.get('rfq_id', 'N/A'), " font-family: monospace;"),
                ("Title", data.get('rfq_title', 'N/A'), ""),
                ("Buyer", data.get('buyer_name', 'N/A'), ""),
                ("Matched Vendors", str(data.get('matched_count', 0)), " font-weight: bold; color: #f97316;"),
                ("Top Match", f"{data.get('top_vendor', 'N/A')} ({data.get('top_score', 0)}%)", "")
            ]
        },
        "quotation_accepted": {
            "color1": "#16a34a", "color2": "#15803d",
            "title": "Quotation Accepted - PO Created",
            "description": "A buyer has accepted a quotation:",
            "rows": [
                ("PO Number", data.get('po_number', 'N/A'), " font-weight: bold; color: #16a34a;"),
                ("Order ID", data.get('order_id', 'N/A'), " font-family: monospace;"),
                ("RFQ Title", data.get('rfq_title', 'N/A'), ""),
                ("Buyer", data.get('buyer_name', 'N/A'), ""),
                ("Vendor", data.get('vendor_name', 'N/A'), ""),
                ("Amount", f"Rs.{data.get('total_amount', 0):,.2f}", " font-weight: bold; font-size: 18px; color: #16a34a;"),
                ("Payment Terms", data.get('payment_terms', 'N/A'), "")
            ]
        },
        "new_po": {
            "color1": "#0891b2", "color2": "#0e7490",
            "title": "New Purchase Order Created",
            "description": "A new purchase order has been created:",
            "rows": [
                ("PO Number", data.get('po_number', 'N/A'), " font-weight: bold; color: #0891b2;"),
                ("Order ID", data.get('order_id', 'N/A'), " font-family: monospace;"),
                ("RFQ Title", data.get('rfq_title', 'N/A'), ""),
                ("Buyer", data.get('buyer_name', 'N/A'), ""),
                ("Vendor", data.get('vendor_name', 'N/A'), ""),
                ("Amount", f"Rs.{data.get('total_amount', 0):,.2f}", " font-weight: bold; font-size: 18px; color: #0891b2;"),
                ("Status", data.get('status', 'N/A'), "")
            ]
        }
    }
    
    template_data = templates.get(template_type, {})
    rows_html = ""
    for label, value, style in template_data.get("rows", []):
        rows_html += row_template.format(label=label, value=value, style=style)
    
    return base_style.format(
        color1=template_data.get("color1", "#1e3a5f"),
        color2=template_data.get("color2", "#2d5a87"),
        title=template_data.get("title", "Notification"),
        description=template_data.get("description", ""),
        rows=rows_html
    )
