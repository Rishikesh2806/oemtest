# OEMLinker - AI-Powered Manufacturing Marketplace PRD

## Brand
- **Name**: OEMLinker (formerly MachinoMatch/Offloadex)
- **Domain**: oemlinker.com
- **Logo**: /logo.png
- **Tagline**: Precision Manufacturing on Demand
- **Email**: notifications@oemlinker.com

## Original Problem Statement
Build an AI-driven on-demand manufacturing marketplace similar to MFG.com/Xometry where buyers upload engineering drawings and RFQs, and vendors are automatically matched based on machine capability, past work, and technical suitability. Platform should intelligently read engineering drawings and extract dimensions/tolerances.

## Architecture Overview
- **Frontend**: React 19 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: OpenAI GPT-5.2 Vision (via Emergent LLM Key)
- **Auth**: JWT + Emergent Google OAuth + 2FA Email OTP
- **Payments**: Stripe (test mode) - planned
- **Email**: Resend API

## Security Features Implemented (Mar 2, 2026)

### Password Security
- Strong password requirements (8+ chars, upper/lower, digit, special)
- Password strength indicator (Weak → Fair → Good → Strong)
- Common pattern detection blocks weak passwords
- Show/hide password toggle

### Login Protection
- Rate limiting: Max 5 failed attempts per 5 minutes
- Account lockout: 15-minute lockout after exceeding attempts
- Prevents user enumeration with generic error messages
- IP logging for all login attempts

### Two-Factor Authentication (2FA)
- Email OTP verification (6-digit code)
- 10-minute OTP expiry
- Max 3 OTP attempts before reset required
- Enable/disable 2FA from account settings
- Resend OTP functionality

### Password Management
- `POST /api/auth/change-password` - Change password (requires current password)
- `POST /api/auth/forgot-password` - Request reset email
- `POST /api/auth/reset-password` - Reset with token (1-hour expiry)

### Security Alerts (Email Notifications)
- Password changed alert with IP and timestamp
- Password reset alert with IP and timestamp
- 2FA enabled/disabled notification

### 2FA Endpoints
- `POST /api/auth/verify-otp` - Verify OTP and complete login
- `POST /api/auth/resend-otp` - Resend OTP code
- `POST /api/auth/2fa/toggle` - Enable/disable 2FA
- `GET /api/auth/2fa/status` - Get current 2FA status

## What's Been Implemented

### Manual Dimension Input Feature (NEW - Mar 2, 2026)
- **PUT /api/rfqs/{rfq_id}/dimensions** - Update dimensions manually when AI can't extract them
- **Enhanced POST /api/rfqs/{rfq_id}/analyze** - Now returns `dimensions_missing` flag and `missing_fields` object
- **CreateRFQ Step 4 UI Enhancement**:
  - Shows AI-extracted specs after analysis
  - Highlights missing dimensions in red/amber
  - Provides input fields for Length, Width, Height, Weight
  - "Save Dimensions" button to update before vendor matching
  - Disables "Find Matching Vendors" until dimensions are provided
- Ensures accurate vendor matching by requiring dimensions

### GSTIN Integration for Vendor Registration (Mar 2, 2026)
- **GET /api/gstin/verify/{gstin}** - Verifies GSTIN and fetches company details
- RegisterPage auto-fills vendor profile fields from GSTIN data
- Extracts: Legal Name, Trade Name, Address, City, State, Pincode

### Notification System Fixes (Mar 2, 2026)
- Fixed redirect for `negotiation_request` notifications (vendors go to RFQ page)
- Fixed redirect for `negotiation_response` notifications (buyers go to RFQ page)
- Updated NotificationBell.jsx and NotificationsPage.jsx

### Quote Detail & Negotiation System (Feb 28, 2026)
- Full negotiation workflow (request, accept, counter, reject)
- QuoteDetailModal with tabs (Details, Vendor Info, Negotiations)
- VendorNegotiationPanel for vendor responses

### Notification System (Feb 28, 2026)
- In-app notifications with bell icon
- NotificationsPage for viewing all notifications
- Real-time badge count with 30-second polling

### Payment Terms System (Feb 27, 2026)
- 9 Payment Term Options
- RFQ, Quote, and Order payment terms flow

### Core Features
- User authentication (JWT + Google OAuth)
- Role-based access control (Buyer, Vendor, Admin)
- AI drawing analysis (GPT-5.2 Vision)
- Smart vendor matching algorithm
- 21 machine categories with conditional dimensions
- Email notifications (Resend)
- Comprehensive Admin Panel

## Test Reports
- /app/test_reports/iteration_1-9.json - Previous features
- /app/test_reports/iteration_10.json - Dimension Input Feature (100% pass)

## Test Credentials
- **Admin**: admin@offoadex.com / admin123
- **Buyer**: buyer@offoadex.com / buyer123
- **Vendor**: info@simpsonmunro.com / vendor123

## Prioritized Backlog

### P0 - Critical (Completed)
- Manual dimension input in RFQ creation ✓
- GSTIN verification for vendor registration ✓
- Notification redirect fixes ✓
- Quote negotiation workflow ✓
- Notification system ✓
- Payment terms ✓

### P1 - High Priority (Next)
- AI Voice Agent for machine availability check
- Stripe payment integration (escrow)
- Revenue analytics charts

### P2 - Medium Priority
- Bulk machine import (CSV)
- WhatsApp/SMS notifications
- Repeat order feature

### P3 - Future
- Instant AI auto-quote
- ERP integration API
- Multi-currency support
- Backend refactoring (break down server.py monolith)

## Key API Endpoints
- PUT /api/rfqs/{rfq_id}/dimensions - Update manual dimensions
- GET /api/gstin/verify/{gstin} - Verify GSTIN
- POST /api/quotes/{quote_id}/negotiate - Start negotiation
- GET /api/notifications - Get notifications

## Known Issues
- External GSTIN API (gstincheck.co.in) may occasionally return errors

## Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions, messages, conversations
- notifications, ratings
