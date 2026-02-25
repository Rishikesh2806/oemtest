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

## Core Requirements (Static)
- Multi-role authentication (Buyer, Vendor, Admin)
- RFQ creation with drawing upload
- AI-powered drawing analysis
- Smart vendor matching algorithm
- Quote submission and comparison
- Order management with payment processing
- Vendor profile and machine capability management
- Buyer-vendor messaging system
- Full admin panel with data management capabilities
- Email notifications for key events
- Drawing view/download functionality

## What's Been Implemented (Feb 2026)

### Backend (FastAPI)
- ✅ User authentication (JWT + Google OAuth)
- ✅ Role-based access control
- ✅ RFQ CRUD operations
- ✅ Drawing upload with base64 storage
- ✅ AI drawing analysis (GPT-5.2 Vision)
- ✅ Vendor matching algorithm (with user_id for chat)
- ✅ Quote management
- ✅ Order creation and tracking
- ✅ Stripe payment integration
- ✅ Dashboard statistics APIs
- ✅ Messaging/Chat APIs
- ✅ Vendor Full Profile API
- ✅ **Admin Management APIs** (users, rfqs, quotes, orders, drawings, vendors, ndas)
- ✅ **Email Notifications (NEW - Feb 25, 2026)**
  - Resend API integration
  - Templates: vendor_matched, quote_received, quote_accepted, order_status_update, new_message
  - Non-blocking async email sending
- ✅ **Drawing View/Download (NEW - Feb 25, 2026)**
  - GET /api/drawings/{id}/view - View in browser (supports token auth in query param)
  - GET /api/drawings/{id}/download - Download as attachment

### Frontend (React)
- ✅ Landing page with hero, features, how-it-works
- ✅ Login/Register with role selection
- ✅ Google OAuth integration
- ✅ Buyer dashboard with stats
- ✅ Multi-step RFQ creation wizard
- ✅ RFQ detail with AI analysis display
- ✅ Vendor dashboard
- ✅ Vendor profile management
- ✅ Machine management (CRUD)
- ✅ Quote submission for vendors
- ✅ Order detail with payment & tracking
- ✅ VendorProfileView page
- ✅ ChatPage (messaging between buyers/vendors)
- ✅ **Admin Dashboard** (8 tabs: Overview, Users, Vendors, RFQs, Quotes, Orders, Drawings, NDAs)
- ✅ **Drawing View/Download buttons (NEW - Feb 25, 2026)**
  - Image preview for supported formats
  - View button (opens in new tab)
  - Download button (triggers file download)

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

## Prioritized Backlog

### P0 - Critical (Completed)
- ✅ Email notifications
- ✅ Drawing view/download
- ✅ Full Admin Panel

### P1 - High Priority (Next)
- [ ] Real vendor data seeding with realistic machine specs
- [ ] Revenue analytics charts on admin dashboard
- [ ] Multi-file drawing upload

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

## Test Credentials
- **Admin**: admin@offoadex.com / admin123
- **Test Buyer**: testbuyer_1772037252@test.com / TestPass123!
- **Test Vendor**: Can register via UI

## Test Reports
- /app/test_reports/iteration_1.json - Chat/Profile features (100% pass)
- /app/test_reports/iteration_2.json - Admin Panel (100% pass)
- /app/test_reports/iteration_3.json - Email & Drawings (100% pass)

## API Keys Configured
- EMERGENT_LLM_KEY: GPT-5.2 Vision for drawing analysis
- STRIPE_API_KEY: Payment processing (test mode)
- RESEND_API_KEY: Email notifications
- SENDER_EMAIL: onboarding@resend.dev

## Next Tasks
1. Seed realistic vendor data with machine specifications
2. Add analytics charts to admin dashboard
3. Improve mobile responsiveness
4. Add vendor rating/review system
