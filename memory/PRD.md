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
- **Enhanced Vendor Matching Algorithm v2.0** (Feb 27)
  - Machine dimension validation (envelope fit check per machine category)
  - Keyword matching from RFQ title/description
  - Vendor past experience scoring
  - Process matching (milling, turning, gear, welding, etc.)
  - Material compatibility check
  - Tolerance capability validation
- Quote management (create, list, accept)
- Order creation and tracking
- Stripe payment integration
- Dashboard statistics APIs
- Messaging/Chat APIs
- Vendor Full Profile API
- Admin Management APIs (users, rfqs, quotes, orders, drawings, vendors, ndas)
- Email Notifications (Resend API integration)
- Drawing View/Download (token-based browser viewing)
- Admin Vendor/Machine Management

### Frontend (React)
- Landing page with hero, features, how-it-works
- Login/Register with role selection
- Google OAuth integration
- Buyer dashboard with stats
- Multi-step RFQ creation wizard
- RFQ detail with AI analysis display
- Enhanced matched vendors display showing:
  - Dimension capability
  - Process matches
  - Keyword matches
  - Experience score
  - Similar jobs count
- Drawing View/Download buttons on RFQ detail
- Vendor dashboard
- Vendor profile management
- Machine management (CRUD) with 21 categories
- Quote submission for vendors
- Quote comparison for buyers
- Order detail with payment & tracking
- VendorProfileView page
- ChatPage (messaging between buyers/vendors)
- Admin Dashboard (8 tabs)
- Admin Vendor Profile Management

### Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions, messages, conversations
- ndas

## Machine Categories (21 types)
1. Turning/Lathe (CNC)
2. Milling (CNC)
3. Vertical Machining Center (VMC)
4. Horizontal Machining Center (HMC)
5. 5-Axis Machining
6. Vertical Turret Lathe (VTL)
7. Boring Machine
8. Drilling/Radial Drilling
9. Gear Hobbing/Shaping
10. Grinding (Surface/Cylindrical)
11. Wire EDM
12. Sinker EDM
13. Laser Cutting
14. Plasma Cutting
15. Waterjet Cutting
16. Press Brake/Sheet Metal
17. Welding (MIG/TIG)
18. Heat Treatment
19. CMM/Inspection
20. Additive Manufacturing
21. Conventional Machines

## Matching Algorithm Scoring (v2.0)
| Component | Max Points | Description |
|-----------|------------|-------------|
| Dimension Capability | 15 | Machine envelope fits part |
| Process Matching | 20-30 | Machine type matches required process |
| Tolerance Capable | 20 | Machine tolerance <= required |
| Materials Match | 15 | Supported materials include required |
| Keyword Matches | 10 | Keywords from title/desc match |
| Experience Score | 20 | Past similar jobs + keywords |
| Vendor Rating | 10 | Rating * 2 |
| Total Jobs | 10 | total_jobs / 10 |
| **Max Total** | **100** | |

## Test Reports
- /app/test_reports/iteration_1.json - Chat/Profile features (100% pass)
- /app/test_reports/iteration_2.json - Admin Panel (100% pass)
- /app/test_reports/iteration_3.json - Email & Drawings (100% pass)
- /app/test_reports/iteration_4.json - Admin Vendor/Machine Management (100% pass)
- /app/test_reports/iteration_5.json - RFQ Matching Algorithm (100% pass - 18 tests)

## Test Credentials
- **Admin**: admin@offoadex.com / admin123

## Prioritized Backlog

### P0 - Critical (Completed)
- Email notifications
- Drawing view/download
- Full Admin Panel
- Admin Vendor/Machine Management
- Enhanced RFQ Matching Algorithm

### P1 - High Priority (Next)
- Quote rejection endpoint (allow buyers to reject quotes explicitly)
- Order Management Module enhancements
- Revenue analytics charts on admin dashboard
- Vendor capacity calendar
- Bulk machine import (CSV)

### P2 - Medium Priority
- WhatsApp/SMS notifications
- Repeat order feature
- Vendor rating system after order completion
- Document version control
- Mobile responsive improvements
- Quote comparison view (side-by-side)

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

## Next Tasks
1. Add explicit quote rejection endpoint for buyers
2. Implement order tracking improvements
3. Add revenue analytics charts to admin dashboard
4. Implement vendor capacity calendar
