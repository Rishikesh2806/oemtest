# OEMLinker - AI-Driven On-Demand Manufacturing Marketplace

## Original Problem Statement
Build a full-stack web application for an AI-driven manufacturing marketplace that handles RFQ-to-payment workflow, RBAC permissions, manual/AI vendor matching, advanced quotation systems, inspection systems, and IP protection.

## Tech Stack
- **Frontend**: React, Shadcn UI, TailwindCSS, Framer Motion
- **Backend**: FastAPI, Pydantic, ReportLab (PDF)
- **Database**: MongoDB
- **Integrations**: AWS S3, OpenAI GPT-5.2 Vision (Emergent LLM Key), Resend, Google OAuth, Razorpay, Gupshup WhatsApp

## Key Credentials
- Admin: admin@offoadex.com / admin123
- Vendor: testvendor_nda@test.com / vendor123
- Buyer: buyer5@oemlinker.com / buyer123

## What's Been Implemented

### Machine Validation Engine v3.0 (Fabrication + Sawing Support)
- Physics-based hard gates (dimension checks, machine type compatibility)
- 5 vendor categories: confirmed_capable, likely_capable, partial_match, excluded_too_small, excluded_wrong_type
- Fabrication operations: welding, riveting, surface_treatment, grinding_deburr, shearing, punching
- Sawing operation (band saw) — excluded from strict matching

### AI Dimension Estimation for Reference Photos
- POST /api/rfqs/{rfq_id}/estimate-dimensions endpoint
- Process-aware schema routing: gear, boring, sheet_metal, **milling (NEW)**, turning, default
- **Bolt hole support**: boring schema includes bolt_hole_diameter, bolt_circle_diameter, number_of_holes
- **Slot support (NEW)**: sheet_metal and milling schemas include slot_length, slot_width, number_of_slots
- **Milling schema (NEW)**: Handles parts with slots, pockets — includes slot_depth, pocket_length/width/depth
- **Improved schema detection priority**: sheet_metal (bend/bracket) checked before boring/drill to avoid misrouting bent parts
- **User dimension preservation**: User-provided dimensions always preserved even if AI schema doesn't include them
- Keyword triggers: "drill/bolt hole/flange" → boring; "slot/pocket/mill" → milling; "sheet/bend/bracket" → sheet_metal

### Send RFQ to Partial Vendors
- POST /api/rfqs/{rfq_id}/send-to-vendor endpoint
- Frontend Send RFQ button on partial/likely vendor rows

### Google OAuth Custom Role Fix
- Email case normalization (.lower()) in google_auth.py
- Custom role users bypass /select-role

### Admin Dashboard
- Demo Panel tab
- Removed all "emergent" text from user-visible code

### Performance
- Fixed duplicate NotificationBell polling
- Polling intervals increased from 30s to 60s

## Pending Issues (Priority Order)
- P0: RFQ PDF single-page layout (recurring, untested for 2+ sessions)
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
- Local desktop model for IP-safe drawing analysis
