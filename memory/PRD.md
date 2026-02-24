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
3. **Admin** - Platform administrators managing approvals

## Core Requirements (Static)
- Multi-role authentication (Buyer, Vendor, Admin)
- RFQ creation with drawing upload
- AI-powered drawing analysis
- Smart vendor matching algorithm
- Quote submission and comparison
- Order management with payment processing
- Vendor profile and machine capability management

## What's Been Implemented (Jan 2026)

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
- ✅ Admin vendor approval system
- ✅ Dashboard statistics APIs

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
- ✅ Admin dashboard for approvals

### Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions

## Prioritized Backlog

### P0 - Critical (Next Sprint)
- [ ] Email notifications for RFQ updates
- [ ] Real vendor data seeding
- [ ] File download for drawings

### P1 - High Priority
- [ ] Chat between buyer & vendor
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

## Next Tasks
1. Add email notifications (SendGrid/Resend)
2. Seed demo vendor data with real machine specs
3. Implement buyer-vendor chat
4. Add analytics charts to dashboards
5. Enhance AI analysis with more drawing formats
