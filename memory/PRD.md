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

### Admin Management APIs (NEW - Feb 25, 2026)
- ✅ **User Management**: GET /api/admin/users, PUT /api/admin/users/{id}, DELETE /api/admin/users/{id}
- ✅ **RFQ Management**: GET /api/admin/rfqs, GET /api/admin/rfqs/{id}, PUT /api/admin/rfqs/{id}, DELETE /api/admin/rfqs/{id}
- ✅ **Quote Management**: GET /api/admin/quotes, PUT /api/admin/quotes/{id}, DELETE /api/admin/quotes/{id}
- ✅ **Order Management**: GET /api/admin/orders, PUT /api/admin/orders/{id}, DELETE /api/admin/orders/{id}
- ✅ **Drawing Management**: GET /api/admin/drawings, GET /api/admin/drawings/{id}, DELETE /api/admin/drawings/{id}
- ✅ **Vendor Management**: GET /api/admin/vendors, PUT /api/admin/vendors/{id}, approve/reject vendors
- ✅ **NDA Management**: POST /api/admin/ndas, GET /api/admin/ndas, PUT /api/admin/ndas/{id}, POST /api/admin/ndas/{id}/send, DELETE /api/admin/ndas/{id}

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

### Admin Dashboard (NEW - Feb 25, 2026)
- ✅ **Overview Tab**: Platform stats (users, vendors, RFQs, quotes, orders, NDAs), pending vendor approvals
- ✅ **Users Tab**: Search, role filter, user table, edit/delete users
- ✅ **Vendors Tab**: Filter by approval status, approve/reject vendors, edit vendor details
- ✅ **RFQs Tab**: Search, status filter, RFQ table with buyer info, edit/delete RFQs
- ✅ **Quotes Tab**: Status filter, quotes table with vendor/RFQ info, edit/delete quotes
- ✅ **Orders Tab**: Status filter, orders table with all party info, edit status/payment, delete orders
- ✅ **Drawings Tab**: Drawings list with AI analysis status, delete drawings
- ✅ **NDAs Tab**: Create new NDA, list NDAs with signature status, edit/send/delete NDAs

### Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions, messages, conversations
- **ndas** (NEW)

## Prioritized Backlog

### P0 - Critical (Next Sprint)
- [ ] Email notifications for RFQ updates
- [ ] Real vendor data seeding
- [ ] File download for drawings

### P1 - High Priority
- ✅ Chat between buyer & vendor (DONE)
- ✅ Full Admin Panel (DONE)
- [ ] Capacity calendar for vendors
- [ ] Revenue analytics charts
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
- **Test Buyer**: Can register via UI
- **Test Vendor**: Can register via UI

## Test Reports
- /app/test_reports/iteration_1.json - Chat/Profile features (100% pass)
- /app/test_reports/iteration_2.json - Admin Panel (100% pass)

## Next Tasks
1. Add email notifications (SendGrid/Resend)
2. Seed demo vendor data with real machine specs
3. Add analytics charts to dashboards
4. Enhance AI analysis with more drawing formats
