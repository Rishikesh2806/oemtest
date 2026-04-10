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
- Test Buyer: testbuyer_cost@test.com / testpass123

## What's Been Implemented

### AI Cost Estimation (NEW - Apr 2026)
- **Admin Cost Config**: GET/PUT `/api/admin/cost-config` — admin-managed rates for materials, machines, finishing, tooling, heat treatment
- **Default rates**: Carbon Steel ₹55/kg, Forged Steel ₹75/kg (as per user), SS304 ₹210/kg, CNC Turning ₹800/hr, CNC Milling ₹1000/hr, etc.
- **Cost Estimation Engine**: POST `/api/rfqs/{rfq_id}/estimate-cost` — AI analyzes part + uses admin rates to produce:
  - Material cost (weight × rate/kg)
  - Per-operation machining cost breakdown (time × rate/hr)
  - Setup/tooling costs
  - Finishing & heat treatment costs
  - Overhead (15%) + profit margin (20%)
  - **Quantity pricing** for 1, 10, 50, 100 pieces with volume discounts (5%/10%/15%)
- **Admin UI**: New "Cost Config" tab in Admin Dashboard with editable rate cards
- **Buyer UI**: "Get Cost Estimate" button in CreateRFQ Step 4 after AI analysis

### AI Dimension Estimation for Reference Photos
- POST /api/rfqs/{rfq_id}/estimate-dimensions endpoint
- Process-aware schema routing: gear, boring, sheet_metal, milling, turning, default
- Bolt hole support: boring schema includes bolt_hole_diameter, bolt_circle_diameter, number_of_holes
- Slot support: sheet_metal and milling schemas include slot_length, slot_width, number_of_slots
- Milling schema: Handles parts with slots, pockets
- User dimension preservation: always preserved even if AI schema doesn't include them

### Machine Validation Engine v3.0
- Physics-based hard gates (dimension checks, machine type compatibility)
- 5 vendor categories: confirmed_capable, likely_capable, partial_match, excluded_too_small, excluded_wrong_type
- Fabrication operations: welding, riveting, surface_treatment, grinding_deburr, shearing, punching

### Google OAuth Custom Role Fix
- Email case normalization (.lower()) in google_auth.py
- Custom role users bypass /select-role

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
