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
- ✅ User authentication (JWT + Google OAuth)
- ✅ Role-based access control
- ✅ RFQ CRUD operations
- ✅ Drawing upload with base64 storage
- ✅ AI drawing analysis (GPT-5.2 Vision)
- ✅ Vendor matching algorithm
- ✅ Quote management
- ✅ Order creation and tracking
- ✅ Stripe payment integration
- ✅ Dashboard statistics APIs
- ✅ Messaging/Chat APIs
- ✅ Vendor Full Profile API
- ✅ **Admin Management APIs** (users, rfqs, quotes, orders, drawings, vendors, ndas)
- ✅ **Email Notifications** (Resend API integration)
- ✅ **Drawing View/Download** (token-based browser viewing)
- ✅ **Admin Vendor Profile Management (NEW - Feb 25)**
  - GET /api/admin/vendors/{id}/full - Full vendor profile with machines and stats
  - PUT /api/admin/vendors/{id}/profile - Update vendor profile
- ✅ **Admin Machine Management (NEW - Feb 25)**
  - GET /api/admin/machines - List all machines (filter by vendor)
  - POST /api/admin/machines - Create machine for any vendor
  - GET /api/admin/machines/{id} - Get machine details
  - PUT /api/admin/machines/{id} - Update any machine
  - DELETE /api/admin/machines/{id} - Delete any machine

### Frontend (React)
- ✅ Landing page with hero, features, how-it-works
- ✅ Login/Register with role selection
- ✅ Google OAuth integration
- ✅ Buyer dashboard with stats
- ✅ Multi-step RFQ creation wizard
- ✅ RFQ detail with AI analysis display
- ✅ **Drawing View/Download buttons** on RFQ detail
- ✅ Vendor dashboard
- ✅ Vendor profile management
- ✅ Machine management (CRUD)
- ✅ Quote submission for vendors
- ✅ Order detail with payment & tracking
- ✅ VendorProfileView page
- ✅ ChatPage (messaging between buyers/vendors)
- ✅ **Admin Dashboard** (8 tabs)
- ✅ **Admin Vendor Profile Management (NEW - Feb 25)**
  - View/Edit vendor profile (company info, certifications, industries, location, rating)
  - Machines list with CRUD operations
  - Add Machine dialog with all fields
  - Edit/Delete machine functionality

### Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions, messages, conversations
- ndas

## Email Notification Triggers
1. **vendor_matched** - When vendor is matched to an RFQ
2. **quote_received** - When buyer receives a quote
3. **quote_accepted** - When vendor's quote is accepted
4. **order_status_update** - When order status changes
5. **new_message** - When user receives a message

## Test Reports
- /app/test_reports/iteration_1.json - Chat/Profile features (100% pass)
- /app/test_reports/iteration_2.json - Admin Panel (100% pass)
- /app/test_reports/iteration_3.json - Email & Drawings (100% pass)
- /app/test_reports/iteration_4.json - Admin Vendor/Machine Management (100% pass)

## Test Credentials
- **Admin**: admin@offoadex.com / admin123

## Prioritized Backlog

### P0 - Critical (Completed)
- ✅ Email notifications
- ✅ Drawing view/download
- ✅ Full Admin Panel
- ✅ Admin Vendor/Machine Management

### P1 - High Priority (Next)
- [ ] Revenue analytics charts on admin dashboard
- [ ] Vendor capacity calendar
- [ ] Bulk machine import (CSV)

### P2 - Medium Priority
- [ ] WhatsApp/SMS notifications
- [ ] Repeat order feature
- [ ] Vendor rating system
- [ ] Document version control
- [ ] Mobile responsive improvements

### P3 - Future Features
- [ ] Instant AI auto-quote
- [ ] Supply chain financing
- [ ] ERP integration API
- [ ] Multi-currency support
- [ ] Mobile app version

## Next Tasks
1. Add revenue analytics charts to admin dashboard
2. Implement vendor capacity calendar
3. Add vendor rating/review system
4. Improve mobile responsiveness
