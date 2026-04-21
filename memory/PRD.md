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

### Code Quality Fixes (Apr 2026)
- Removed hardcoded JWT secrets from `auth.py`, `demo.py`, `server.py` — all now read from `JWT_SECRET_KEY` env var
- Fixed 6 backend lint issues: redefined class, unused vars, f-strings without placeholders
- Added `eslint-disable` annotations for 30+ intentional mount-only useEffect hooks across all pages
- Replaced array index keys with stable string keys in VendorDetail, VendorDirectory
- Shared `PublicNav` component with mobile hamburger menu across all public pages

### Browse Before Registering (Apr 2026)
- Public RFQ Marketplace (`/rfqs`), Machine/Capabilities Directory (`/machines`)
- Drawing Thumbnails with NDA blurring, PIL crash fix for truncated images
- Consistent navigation with mobile hamburger menu

### AI Cost Estimation (Apr 2026)
- Admin-managed rates, AI engine with drawing analysis, volume discounts, buyer-material exclusion

### Core Platform
- Multi-operation AI vendor matching engine, GPT-5.2 drawing analysis
- Custom Google OAuth, Razorpay payments, WhatsApp integration
- RFQ-to-order workflow, NDA enforcement, inspection system

## Pending Issues
- P0: RFQ PDF single-page layout (recurring 3+ sessions, untested)
- P2: 2.5% commission UI in BuyerQuotes

## Upcoming Tasks
- Few-shot prompt training for Drawing Analysis (P1)
- WhatsApp & AI Call Machine Availability Check (P1)
- Textile/Fabric Vertical Addition (P1)
- Stripe Escrow Integration (P1)
- ElevenLabs Voice Integration (P1)
- server.py refactoring Phase 2 (P1)

## Future/Backlog
- Instant AI auto-quote for simple parts
- API for ERP integration
- Homepage redesign
