# Offoadex.com - AI-Powered Manufacturing Marketplace PRD

## Original Problem Statement
Build an AI-driven on-demand manufacturing marketplace similar to MFG.com/Xometry where buyers upload engineering drawings and RFQs, and vendors are automatically matched based on machine capability, past work, and technical suitability. Platform should intelligently read engineering drawings and extract dimensions/tolerances.

## Architecture Overview
- **Frontend**: React 19 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: OpenAI GPT-5.2 Vision (via Emergent LLM Key)
- **Auth**: JWT + Emergent Google OAuth
- **Payments**: Stripe (test mode)
- **Email**: Resend API

## User Personas
1. **Buyer** - Engineers/procurement teams sourcing manufacturing services
2. **Vendor** - Machine shops/manufacturers offering services
3. **Admin** - Platform administrators with full CRUD access to all data

## What's Been Implemented (Feb 2026)

### Backend (FastAPI)
- User authentication (JWT + Google OAuth)
- Role-based access control
- RFQ CRUD operations
- Drawing upload with base64 storage
- AI drawing analysis (GPT-5.2 Vision)
- **Enhanced Vendor Matching Algorithm v2.0**
  - Machine dimension validation
  - Keyword matching from RFQ title/description
  - Vendor past experience scoring
  - Process, material, tolerance matching
- Quote management (create, list, accept)
- **Enriched Quotes API** - Returns vendor machines, certifications, acceptance_rate
- **Vendor Rating System** (Feb 27) - NEW
  - POST /api/orders/{order_id}/rate - Submit rating (1-5 scale for overall, quality, communication, delivery)
  - GET /api/vendors/{vendor_id}/ratings - Get ratings with stats
  - GET /api/orders/{order_id}/rating - Check if order rated
  - Auto-updates vendor average rating
- **Enhanced Order Management** (Feb 27) - NEW
  - GET /api/orders/{order_id}/details - Full order details with vendor, buyer, quote, rfq
  - POST /api/orders/{order_id}/confirm-delivery - Buyer confirms delivery
  - POST /api/orders/{order_id}/add-tracking - Vendor adds shipping info
- Stripe payment integration
- Dashboard statistics APIs
- Messaging/Chat APIs
- Admin Management APIs
- Email Notifications (Resend)
- Drawing View/Download

### Frontend (React)
- Landing page with hero, features, how-it-works
- Login/Register with role selection
- Google OAuth integration
- Buyer/Vendor dashboards
- Multi-step RFQ creation wizard
- RFQ detail with AI analysis display
- Enhanced matched vendors display
- Drawing View/Download buttons
- Machine management (CRUD) with 21 categories
- **Quote Comparison Feature** - Side-by-side comparison with badges
- **Enhanced OrderDetail Page** (Feb 27) - NEW
  - Rating dialog with star ratings for overall/quality/communication/delivery
  - Tracking info display
  - Confirm Delivery button for buyers
  - Add Tracking dialog for vendors
  - Your Rating section when rated
- **VendorProfileView with Reviews** (Feb 27) - NEW
  - Customer Reviews section
  - Rating stats (overall, quality, communication, delivery, recommendation rate)
  - Individual review display with buyer info, review text, scores
- ChatPage (messaging)
- Admin Dashboard (8 tabs)

### Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions, messages, conversations
- ndas, **ratings** (NEW)

## Rating System
- **Rating Categories**: Overall, Quality, Communication, Delivery (1-5 stars)
- **Validation**: Buyer role only, Delivered/Completed orders only, One rating per order
- **Review**: Optional text review + "Would Recommend" flag
- **Stats**: Averages for each category + recommendation percentage

## Order Status Flow
1. pending_payment - Quote accepted, awaiting payment
2. paid - Payment confirmed
3. in_production - Vendor started production
4. quality_check - Quality inspection in progress
5. dispatched - Shipped with tracking info
6. delivered - Delivery confirmed by buyer
7. completed - Order rated and closed

## Test Reports
- /app/test_reports/iteration_1.json - Chat/Profile features (100% pass)
- /app/test_reports/iteration_2.json - Admin Panel (100% pass)
- /app/test_reports/iteration_3.json - Email & Drawings (100% pass)
- /app/test_reports/iteration_4.json - Admin Vendor/Machine Management (100% pass)
- /app/test_reports/iteration_5.json - RFQ Matching Algorithm (100% pass - 18 tests)
- /app/test_reports/iteration_6.json - Quote Comparison (100% pass - 15 tests)
- /app/test_reports/iteration_7.json - Rating & Order Management (100% pass - 16 tests)

## Test Credentials
- **Admin**: admin@offoadex.com / admin123
- **Buyer**: buyer@offoadex.com / buyer123

## Prioritized Backlog

### P0 - Critical (Completed)
- Email notifications
- Drawing view/download
- Full Admin Panel
- Admin Vendor/Machine Management
- Enhanced RFQ Matching Algorithm
- Quote Comparison Feature
- Vendor Rating System
- Enhanced Order Management

### P1 - High Priority (Next)
- Revenue analytics charts on admin dashboard
- Vendor capacity calendar
- Bulk machine import (CSV)
- Quote rejection endpoint (explicit reject)

### P2 - Medium Priority
- WhatsApp/SMS notifications
- Repeat order feature
- Document version control
- Mobile responsive improvements

### P3 - Future Features
- Instant AI auto-quote
- Supply chain financing
- ERP integration API
- Multi-currency support
- Mobile app version

## Known Issues
- None

## Bug Fixes (Feb 27, 2026)
- Fixed `AttributeError` in match_vendors when `ai_analysis` is None
- Fixed email sending in confirm-delivery and add-tracking endpoints

## Next Tasks
1. Add revenue analytics charts to admin dashboard
2. Implement vendor capacity calendar
3. Add bulk machine import (CSV upload)
