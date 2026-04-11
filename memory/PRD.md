# OEMLinker - AI-Driven On-Demand Manufacturing Marketplace

## Original Problem Statement
Build a full-stack web application for an AI-driven manufacturing marketplace that handles RFQ-to-payment workflow, RBAC permissions, manual/AI vendor matching, advanced quotation systems, inspection systems, and IP protection.

## Tech Stack
- **Frontend**: React, Shadcn UI, TailwindCSS, Framer Motion
- **Backend**: FastAPI, Pydantic, ReportLab (PDF)
- **Database**: MongoDB
- **Integrations**: AWS S3, OpenAI GPT-5.2 Vision (Emergent LLM Key), Resend, Google OAuth, Razorpay, Gupshup WhatsApp
- **Utilities**: pdf2image + poppler-utils, Pillow (thumbnails)

## What's Been Implemented

### Browse Before Registering (Apr 2026)
- **Public RFQ Marketplace** (`/rfqs`): Browse RFQs with drawing previews, materials, processes — no login
- **Public Machine Directory** (`/machines`): Browse CNC machines, work envelopes, tolerances — no login
- **Public Vendor Directory** (`/vendors`): Browse manufacturers (links hidden per user request)
- **Drawing Thumbnails**: `GET /api/public/drawings/{id}/thumbnail` — serves resized images (supports PNG/JPEG/PDF), handles truncated images
- **Status-sorted RFQs**: Open/unquoted on top, quoted/expired below
- **Quote button**: On each open RFQ card → triggers vendor registration modal
- **Auth Gate Modal**: Role-specific CTA for unauthenticated users
- **Consistent Navigation**: All public pages use same logo, menu, and header as landing page (Apr 2026)

### AI Cost Estimation (Apr 2026)
- Admin-managed rates (material/kg, machine/hr, finishing, tooling, heat treatment)
- AI engine uses drawing image + admin rates for full breakdown
- PDF drawings auto-converted to JPEG for GPT Vision
- Quantity pricing (1, 10, 50, 100 pcs) with volume discounts
- Buyer-material exclusion: material cost zeroed when buyer provides material
- Beta disclaimer

### AI Dimension Estimation
- Process-aware schema routing: gear, boring, sheet_metal, milling, turning, default
- Bolt hole + slot support in schemas

### Machine Validation Engine v3.0
- Physics-based hard gates, 5 vendor categories
- Fabrication operations support

## Pending Issues (Priority Order)
- P0: RFQ PDF single-page layout (recurring 3+ sessions, untested)
- P2: 2.5% commission UI in BuyerQuotes

## Upcoming Tasks
- Few-shot prompt training for Drawing Analysis (P1)
- WhatsApp & AI Call Machine Availability Check (P1)
- Textile/Fabric Vertical Addition (P1)
- ElevenLabs Voice Integration (P1)
- Stripe Escrow Integration (P1)
- server.py refactoring Phase 2

## Future/Backlog
- Instant AI auto-quote for simple parts
- API for ERP integration
- Homepage redesign
