# OEMLinker - AI-Driven On-Demand Manufacturing Marketplace

## Original Problem Statement
Build a full-stack web application for an AI-driven manufacturing marketplace that handles RFQ-to-payment workflow, RBAC permissions, manual/AI vendor matching, advanced quotation systems, inspection systems, and IP protection.

## Tech Stack
- **Frontend**: React, Shadcn UI, TailwindCSS, Framer Motion
- **Backend**: FastAPI, Pydantic, ReportLab (PDF)
- **Database**: MongoDB
- **Integrations**: AWS S3, OpenAI GPT-5.2 Vision (Emergent LLM Key), Resend, Google OAuth, Razorpay, Gupshup WhatsApp

## Core Architecture
```
/app/
├── backend/
│   ├── app/
│   │   ├── routes/ (auth, chatbot, google_auth, orders, vendor)
│   │   ├── services/
│   │   │   └── machine_validation.py  # Strict physics-based engine
│   ├── server.py                      # Monolith (needs continued refactoring)
└── frontend/
    └── src/
        ├── components/
        │   └── ExcludedVendorsSection.jsx  # Partial/Likely vendor display + Send RFQ
        ├── pages/
        │   ├── CreateRFQ.jsx               # RFQ creation flow with inline partial results
        │   └── RFQDetail.jsx               # RFQ detail with vendor categories
```

## Key Credentials
- Admin: admin@offoadex.com / admin123
- Vendor: testvendor_nda@test.com / vendor123
- Buyer: visualbuyer@test.com / buyer123

## What's Been Implemented

### Machine Validation Engine v2.0
- Physics-based hard gates (dimension checks, machine type compatibility)
- 5 vendor categories: confirmed_capable, likely_capable, partial_match, excluded_too_small, excluded_wrong_type
- Sawing operation support (band saw) - correctly separates from laser_cutting
- Facing dimension rules with length check (prevents VTL matching for long shafts)
- Sawing excluded from strict matching (basic prep step, not a differentiator)

### Send RFQ to Partial Vendors
- POST /api/rfqs/{rfq_id}/send-to-vendor endpoint
- Moves vendor from partial/likely lists to matched_vendors
- Sends email + WhatsApp + in-app notifications
- Frontend: Send RFQ button on each partial/likely vendor row
- Auto-opens Partial Match section in ExcludedVendorsSection

### RFQ Creation Flow - Inline Partial Results
- When no confirmed vendors match, shows partial/likely results inline
- "No Exact Matches — But Close Ones Found" with Send RFQ buttons
- Falls back to generic "No Exact Matches Right Now" when no partial either

### Other Completed Features
- AI Drawing Analysis (GPT-5.2 Vision)
- Custom Google OAuth
- AI Chatbot (Gemini 3 Flash) with feedback + analytics
- Contact page with Google Maps + Resend emails
- NDA enforcement on drawings
- RFQ PDF generation (ReportLab)
- Admin dashboard with vendor management

## Pending Issues (Priority Order)
- P0: RFQ PDF single-page layout (in progress, untested)
- P1: 2.5% commission UI in BuyerQuotes (recurring, missed twice)
- P2: Few-shot prompt training for drawing analysis

## In Progress
- server.py refactoring Phase 2 (extract RFQ, Admin, Inspection routes)

## Upcoming Tasks
- WhatsApp & AI Call Machine Availability Check (P1)
- RFQ Expiry Filtering (P1)
- Textile/Fabric Vertical Addition (P1)
- ElevenLabs Voice Integration (P1)
- Stripe Escrow Integration (P1)

## Future/Backlog
- Instant AI auto-quote for simple parts
- API for ERP integration
- WhatsApp image population fix
