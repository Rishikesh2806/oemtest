# OEMLinker - AI-Driven On-Demand Manufacturing Marketplace

## Original Problem Statement
Build a full-stack web application for an AI-driven manufacturing marketplace that handles RFQ-to-payment workflow, RBAC permissions, manual/AI vendor matching, advanced quotation systems, inspection systems, and IP protection.

## Tech Stack
- **Frontend**: React, Shadcn UI, TailwindCSS, Framer Motion
- **Backend**: FastAPI, Pydantic, ReportLab (PDF)
- **Database**: MongoDB
- **Integrations**: AWS S3, OpenAI GPT-5.2 Vision (Emergent LLM Key), Resend, Google OAuth, Razorpay, Gupshup WhatsApp
- **Utilities**: pdf2image + poppler-utils (PDF→image for AI vision)

## Key Credentials
- Admin: admin@offoadex.com / admin123
- Vendor: testvendor_nda@test.com / vendor123

## What's Been Implemented

### AI Cost Estimation (Apr 2026)
- **Admin Cost Config**: GET/PUT `/api/admin/cost-config` — admin-managed rates
- **Default rates**: Carbon Steel ₹55/kg, Forged Steel ₹75/kg, SS304 ₹210/kg, CNC Turning ₹800/hr, etc.
- **Cost Estimation Engine**: POST `/api/rfqs/{rfq_id}/estimate-cost`
  - AI analyzes drawing image + admin rates → full cost breakdown
  - PDF drawings auto-converted to JPEG for GPT Vision
  - Reads weight from drawing title block when available
  - Material, per-operation machining, setup, tooling, finishing, heat treatment
  - Overhead (15%) + profit margin (20%)
  - Quantity pricing (1, 10, 50, 100 pcs) with volume discounts
- **Admin UI**: "Cost Config" tab in Admin Dashboard
- **Buyer UI**: "Get Cost Estimate" button in CreateRFQ Step 4

### AI Dimension Estimation
- Process-aware schema routing: gear, boring, sheet_metal, milling, turning, default
- Bolt hole + slot support in schemas
- User dimension preservation

### Machine Validation Engine v3.0
- Physics-based hard gates, 5 vendor categories
- Fabrication operations: welding, riveting, surface treatment, etc.

### AI Drawing Analysis
- GPT-5.2 Vision extracts dimensions, processes, tolerances from drawings
- NOW extracts weight_kg from title block (rule 12 added)

## Pending Issues (Priority Order)
- P0: RFQ PDF single-page layout (recurring, untested for 2+ sessions)
- P1: 2.5% commission UI in BuyerQuotes
- P2: Few-shot prompt training for drawing analysis

## In Progress
- server.py refactoring Phase 2

## Upcoming Tasks
- WhatsApp & AI Call Machine Availability Check (P1)
- Textile/Fabric Vertical Addition (P1)
- ElevenLabs Voice Integration (P1)
- Stripe Escrow Integration (P1)

## Future/Backlog
- Instant AI auto-quote for simple parts
- API for ERP integration
- WhatsApp image population fix
