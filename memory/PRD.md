# OEMLinker - AI-Powered Manufacturing Marketplace PRD

## Brand
- **Name**: OEMLinker (formerly MachinoMatch/Offloadex)
- **Domain**: oemlinker.com
- **Logo**: /logo.png
- **Tagline**: Precision Manufacturing on Demand
- **Email**: notifications@oemlinker.com

## Original Problem Statement
Build an AI-driven on-demand manufacturing marketplace similar to MFG.com/Xometry where buyers upload engineering drawings and RFQs, and vendors are automatically matched based on machine capability, past work, and technical suitability. Platform should intelligently read engineering drawings and extract dimensions/tolerances.

## Architecture Overview
- **Frontend**: React 19 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python) - Refactored modular structure
- **Database**: MongoDB
- **AI**: OpenAI GPT-5.2 Vision (via Emergent LLM Key)
- **Auth**: JWT + Emergent Google OAuth + 2FA Email OTP
- **Payments**: Stripe (test mode) - planned
- **Email**: Resend API

### Backend Structure (Refactored Mar 6, 2026)
```
/app/backend/
├── app/                    # Modular package
│   ├── config.py           # Settings, constants
│   ├── database.py         # MongoDB connection
│   ├── dependencies.py     # Auth helpers (get_current_user)
│   ├── main.py             # FastAPI app factory
│   ├── models/             # Pydantic models (7 files)
│   ├── services/           # security.py, email_service.py
│   └── routes/             # auth.py (15 endpoints), users.py (2 endpoints)
├── server.py               # Main entry (~7500 lines)
└── .env
```
Migration: Phase 1-2 done (models, services, auth routes). Phase 3 next (vendor/RFQ routes).

## AI Drawing Analysis - Supported Formats

### Supported for AI Analysis:
- **PDF** - Best quality, recommended
- **PNG/JPG** - High-resolution images work well
- The AI can extract dimensions, tolerances, materials, and manufacturing specifications

### Not Supported for AI Analysis (Mar 4, 2026):
- **DWG** (AutoCAD native format) - Requires PDF/image export
- **STEP/STP** (3D CAD exchange format) - Requires PDF/image export
- **DXF** (Drawing Exchange Format) - Requires PDF/image export
- **IGES/IGS** (CAD exchange format) - Requires PDF/image export
- **CATPART, SLDPRT, PRT** (Native CAD) - Requires PDF/image export

**Note**: CAD files can still be uploaded for reference but must be exported to PDF or high-res image for AI analysis. Users receive clear error message with export instructions.

## Security Features Implemented (Mar 2, 2026)

### Password Security
- Strong password requirements (8+ chars, upper/lower, digit, special)
- Password strength indicator (Weak → Fair → Good → Strong)
- Common pattern detection blocks weak passwords
- Show/hide password toggle

### Login Protection
- Rate limiting: Max 5 failed attempts per 5 minutes
- Account lockout: 15-minute lockout after exceeding attempts
- Prevents user enumeration with generic error messages
- IP logging for all login attempts

### Two-Factor Authentication (2FA)
- Email OTP verification (6-digit code)
- 10-minute OTP expiry
- Max 3 OTP attempts before reset required
- Enable/disable 2FA from account settings
- Resend OTP functionality

### Password Management
- `POST /api/auth/change-password` - Change password (requires current password)
- `POST /api/auth/forgot-password` - Request reset email
- `POST /api/auth/reset-password` - Reset with token (1-hour expiry)

### Security Alerts (Email Notifications)
- Password changed alert with IP and timestamp
- Password reset alert with IP and timestamp
- 2FA enabled/disabled notification

### 2FA Endpoints
- `POST /api/auth/verify-otp` - Verify OTP and complete login
- `POST /api/auth/resend-otp` - Resend OTP code
- `POST /api/auth/2fa/toggle` - Enable/disable 2FA
- `GET /api/auth/2fa/status` - Get current 2FA status

## What's Been Implemented

### Vendor Location Preference Matching (NEW - Mar 2, 2026)
- **Enhanced RFQ Creation**: Buyers can specify:
  - Delivery Location (address, city, state, country, pincode)
  - Incoterms (EXW, FOB, CIF, etc.)
  - Preferred Vendor Countries (list)
  - Preferred Vendor Cities (list)
- **Smart Location Scoring in Vendor Matching**:
  - +15 points for vendors in preferred cities
  - +10 points for vendors in preferred countries
  - Returns `location_match` ('city', 'country', or null) per vendor
  - Returns `location_score` per vendor
- **RFQ Detail View for Vendors**: Shows all delivery and shipping preference info
- **Test Report**: /app/test_reports/iteration_11.json (100% pass)

### Manual Dimension Input Feature (NEW - Mar 2, 2026)
- **PUT /api/rfqs/{rfq_id}/dimensions** - Update dimensions manually when AI can't extract them
- **Enhanced POST /api/rfqs/{rfq_id}/analyze** - Now returns `dimensions_missing` flag and `missing_fields` object
- **CreateRFQ Step 4 UI Enhancement**:
  - Shows AI-extracted specs after analysis
  - Highlights missing dimensions in red/amber
  - Provides input fields for Length, Width, Height, Weight
  - "Save Dimensions" button to update before vendor matching
  - Disables "Find Matching Vendors" until dimensions are provided
- Ensures accurate vendor matching by requiring dimensions

### GSTIN Integration for Vendor Registration (Mar 2, 2026)
- **GET /api/gstin/verify/{gstin}** - Verifies GSTIN and fetches company details
- RegisterPage auto-fills vendor profile fields from GSTIN data
- Extracts: Legal Name, Trade Name, Address, City, State, Pincode

### Notification System Fixes (Mar 2, 2026)
- Fixed redirect for `negotiation_request` notifications (vendors go to RFQ page)
- Fixed redirect for `negotiation_response` notifications (buyers go to RFQ page)
- Updated NotificationBell.jsx and NotificationsPage.jsx

### Quote Detail & Negotiation System (Feb 28, 2026)
- Full negotiation workflow (request, accept, counter, reject)
- QuoteDetailModal with tabs (Details, Vendor Info, Negotiations)
- VendorNegotiationPanel for vendor responses

### Notification System (Feb 28, 2026)
- In-app notifications with bell icon
- NotificationsPage for viewing all notifications
- Real-time badge count with 30-second polling

### Payment Terms System (Feb 27, 2026)
- 9 Payment Term Options
- RFQ, Quote, and Order payment terms flow

### Core Features
- User authentication (JWT + Google OAuth)
- Role-based access control (Buyer, Vendor, Admin)
- AI drawing analysis (GPT-5.2 Vision)
- Smart vendor matching algorithm
- 21 machine categories with conditional dimensions
- Email notifications (Resend)
- Comprehensive Admin Panel

## Test Reports
- /app/test_reports/iteration_1-9.json - Previous features
- /app/test_reports/iteration_10.json - Dimension Input Feature (100% pass)
- /app/test_reports/iteration_11.json - Vendor Location Matching (100% pass)
- /app/test_reports/iteration_12.json - RFQ Urgency Feature (100% pass)
- /app/test_reports/iteration_13.json - Availability Prioritization (100% pass)

## Legal Pages (Added Mar 7, 2026)
Professional legal documentation for platform compliance:
- **Terms of Service** (/terms-of-service): 14 comprehensive sections covering:
  - Definitions, Eligibility, Platform Services
  - Buyer & Vendor Terms
  - Payments, Fees, Escrow
  - Dispute Resolution
  - Intellectual Property
  - Limitation of Liability
  - Termination, Governing Law (India)
- **Privacy Policy** (/privacy-policy): 14 comprehensive sections covering:
  - Information Collection (provided, automatic, third-party)
  - AI & Machine Learning data practices
  - Data Sharing & Disclosure rules
  - Security measures (SSL, encryption, 2FA)
  - Data Retention periods
  - User Rights (access, correction, deletion, portability)
  - Cookies policy
  - Grievance Officer details (Indian IT Act compliance)
- **Footer Links**: Added to landing page with Terms, Privacy, Contact links

## Dispute Resolution System (Added Mar 6, 2026)
Complete dispute management system for handling conflicts:
- **Dispute Types**: Quality Issue, Delivery Delay, Wrong Specifications, Payment Issue, Communication, Damaged Goods, Incomplete Order, Other
- **Status Flow**: Open → Under Review → Awaiting Response → Escalated → Resolved → Closed
- **Resolution Types**: Full Refund, Partial Refund, Replacement, Rework, No Action, Mutual Agreement
- **Features**:
  - Raise dispute from Order Detail page (Buyer/Vendor)
  - Timeline with all responses and status changes
  - Evidence attachment support
  - Admin resolution panel with refund amount entry
  - Email notifications for dispute events
  - Status filtering and search on Disputes page
- **Routes**: /disputes, /disputes/:disputeId
- **API Endpoints**: POST /disputes, GET /disputes, GET /disputes/:id, POST /disputes/:id/respond, PUT /disputes/:id/status, PUT /disputes/:id/resolve, GET /orders/:id/dispute

## Admin Analytics Dashboard (Added Mar 6, 2026)
Comprehensive platform analytics for business tracking:
- **Key Metrics**: Users, RFQs, Quotes, Orders, Revenue, GMV
- **Platform Health**: RFQ Match Rate, Quote Conversion, Vendor Approval, Machine Availability
- **Revenue Trend**: 6-month bar chart with total/paid/pending breakdown
- **User Breakdown**: Buyers vs Vendors, verification rate, new users (today/week/month)
- **RFQ Analysis**: Status distribution, urgency breakdown, match statistics
- **Quote Metrics**: Conversion rate, accepted/pending/rejected, avg quote value
- **Order Status**: Status distribution, completion tracking
- **Vendor Statistics**: Approval rate, top vendors by jobs with ratings
- **Machine Statistics**: Availability, category distribution
- **Recent Activity**: Latest users, RFQs, quotes, orders with timestamps
- **Export**: CSV export of order data
- **Auto-refresh**: Every 5 minutes
- **Route**: /admin/analytics

## Test Credentials
- **Admin**: admin@offoadex.com / admin123
- **Test Buyer**: testbuyer_loc@test.com / SecureP@ss#7291
- **Test Vendor**: testvendor_loc@test.com / SecureV@nd0r#729

## Prioritized Backlog

### P0 - Critical (Completed)
- Vendor location preference matching ✓
- Vendor past experience in profile for improved matching ✓
- Conventional/heavy machine detection for rough machining ✓
- Manual dimension input in RFQ creation ✓
- GSTIN verification for vendor registration ✓
- Notification redirect fixes ✓
- Quote negotiation workflow ✓
- Notification system ✓
- Payment terms ✓
- RFQ Urgency & Deadline feature ✓ (Mar 6, 2026)
- Availability prioritization for urgent RFQs ✓ (Mar 6, 2026)

### P1 - High Priority (Next)
- AI Voice Agent for machine availability check
- Stripe payment integration (escrow)
- Revenue analytics charts

### P2 - Medium Priority
- SMS notifications (Phone OTP)
- Repeat order feature

### Completed (P2)
- WhatsApp notifications ✓ (Mar 7, 2026) - Gupshup integration
- Bulk Machine Import (CSV) ✓ (Mar 7, 2026)

### P3 - Future
- Instant AI auto-quote
- ERP integration API
- Multi-currency support
- Backend refactoring (break down server.py monolith)

## Key API Endpoints
- POST /api/rfqs/{rfq_id}/match - Smart vendor matching with location scoring + text dimension extraction
- POST /api/rfqs/{rfq_id}/analyze - AI drawing analysis with title/description fallback
- POST /api/vendors/experiences - Add past experience
- GET /api/vendors/experiences - Get vendor's past experiences
- PUT /api/rfqs/{rfq_id}/dimensions - Update manual dimensions
- GET /api/gstin/verify/{gstin} - Verify GSTIN
- POST /api/quotes/{quote_id}/negotiate - Start negotiation
- GET /api/notifications - Get notifications

## Known Issues
- External GSTIN API (gstincheck.co.in) may occasionally return errors

## Admin Notifications (Added Mar 5, 2026)
Admin receives email notifications at `oemlinker@gmail.com` for:
- New user registrations
- New RFQ created
- New quotation submitted
- Vendor matching completed
- Quotation accepted
- New PO created

## RFQ Urgency Feature (Added Mar 6, 2026)
Allow buyers to specify urgency level and deadline for RFQs:
- **Urgency Levels**: Urgent (🔴), High Priority (🟠), Normal (🟢), Low Priority (🔵)
- **Deadline Field**: Optional date picker for delivery deadline
- **UI Display**: 
  - Create RFQ page (Step 1): Urgency dropdown + Deadline input after Surface Finish
  - RFQ Detail page: Urgency badge in header (for non-normal), colored urgency row with deadline
- **Color Coding**: Red for urgent, orange for high, green for normal, blue for low
- **Test Report**: /app/test_reports/iteration_12.json (100% pass)

## Availability Prioritization for Urgent RFQs (Added Mar 6, 2026)
Enhanced vendor matching algorithm to prioritize vendors with available machines for urgent jobs:
- **Availability Scoring**: +10-20 bonus points for vendors with available machines on urgent/high priority RFQs
- **Score Penalty**: Vendors without available machines get 20% penalty for urgent RFQs
- **Machine Status Tracking**: Each machine shows availability status (available, engaged, maintenance, offline)
- **Smart Deadline Check**: If machine is engaged but will be free before RFQ deadline, it's still considered
- **Frontend Display**:
  - "Available Now" badge (emerald with pulsing dot) for vendors with available machines
  - Machine availability count (X/Y Available) in Matching Machines section
  - Green/Amber status indicators on individual machines
- **Test Report**: /app/test_reports/iteration_13.json (100% pass)

## Voice Agent (Added Mar 5, 2026)
Web-based voice assistant for vendors to query matched RFQs:
- Speech-to-text using OpenAI Whisper
- AI-powered response generation using GPT-4o-mini
- Text-to-speech using OpenAI TTS (Nova voice)
- Accessible via "Voice Assistant" button on Vendor Dashboard
- Features: Microphone recording, sample questions, audio playback
- **Past Experience Persistence Fixed**: The PUT `/api/vendors/profile` endpoint was overwriting `past_experiences` with an empty array when saving profile changes. Fixed by excluding `past_experiences` from the `$set` operation - experiences are now managed separately via `/vendors/experiences` endpoints.

## WhatsApp Integration via Gupshup (Added Mar 7, 2026)
WhatsApp Business API integration for vendor communication:
- **Provider**: Gupshup (https://www.gupshup.io)
- **App Name**: OEMLinker
- **Source Number**: 919831509919

### Features:
- **Vendor Notifications**: Notify matched vendors about new RFQs via WhatsApp
- **AI-Powered Chat**: Vendors can query RFQs, quotes, orders via WhatsApp messages
- **🎤 Voice Search**: Vendors can send voice messages - transcribed via Whisper and processed
- **Commands**: `help`, `rfqs`, `details <id>`, `my quotes`, `my orders`, `profile`
- **Natural Language**: AI responds to vendor queries in conversational format
- **Webhook**: Receives incoming WhatsApp messages at `/api/whatsapp/webhook`
- **Multi-language Support**: Whisper supports all Indian languages for voice messages

### Voice Search Flow:
1. Vendor sends voice message → WhatsApp
2. Webhook receives audio URL from Gupshup
3. Audio downloaded and transcribed via OpenAI Whisper
4. AI processes transcribed query
5. Text response sent back (+ confirmation of transcription)
6. **Audio response sent via TTS** (OpenAI Nova voice)

### Audio Response Flow:
1. AI generates text response
2. OpenAI TTS converts text to audio (Nova voice)
3. Audio uploaded to Gupshup Media API
4. Audio message sent to vendor via WhatsApp

### Admin Features:
- Send text messages
- **Send voice messages** (TTS generated)
- View webhook URL for configuration

### API Endpoints:
- `GET /api/whatsapp/status` - Check integration status (public)
- `POST /api/whatsapp/send` - Send message (admin only)
- `POST /api/whatsapp/notify-rfq?rfq_id=xxx` - Notify vendors about RFQ (admin/buyer)
- `POST /api/whatsapp/webhook` - Receive incoming messages (public)

### Frontend:
- **Admin Page**: `/admin/whatsapp` - View status, send test messages, webhook URL
- **RFQ Detail**: "Notify via WhatsApp" button for buyers with matched vendors

### Files:
- `/app/backend/app/services/whatsapp_service.py` - Gupshup API service
- `/app/backend/server.py` - WhatsApp endpoints (lines 8286+)
- `/app/frontend/src/pages/WhatsAppAdmin.jsx` - Admin management page

### Test Report: /app/test_reports/iteration_14.json (100% pass)

## Bulk Machine Import via CSV (Added Mar 7, 2026)
Allows vendors to upload CSV files to import multiple machines at once:

### Features:
- **CSV Template**: Downloadable template with sample data and instructions
- **Drag-and-Drop Upload**: Easy file upload with visual feedback
- **Smart Validation**: Required fields check (machine_type, brand, model)
- **Partial Import**: Valid rows are imported, invalid rows skipped with error details
- **Error Reporting**: Per-row error messages with row numbers
- **Success Summary**: Shows total, imported, and failed counts

### API Endpoints:
- `GET /api/machines/bulk-import/template` - Download CSV template with instructions
- `POST /api/machines/bulk-import` - Upload CSV file (vendor only)

### CSV Fields:
- Required: `machine_type`, `brand`, `model`
- Optional: `name`, `machine_category`, `max_x`, `max_y`, `max_z`, `max_diameter`, `max_length`, `max_swing`, `tolerance`, `materials_supported`, `monthly_capacity_hours`

### Files:
- `/app/backend/server.py` - Bulk import endpoints (lines 2920-3100)
- `/app/frontend/src/pages/MachineManagement.jsx` - Bulk import UI

### Test Report: /app/test_reports/iteration_15.json (100% pass)

## Vendor Registration via WhatsApp GST Certificate Upload (Added Mar 7, 2026)
Allows vendors to register on OEMLinker by uploading their GST certificate image via WhatsApp:

### Features:
- **Image Processing**: Upload GST certificate image via WhatsApp
- **AI GSTIN Extraction**: OpenAI Vision extracts GSTIN from the certificate
- **Auto-Validation**: Validates GSTIN format (15-char pattern with state code and Z at position 13)
- **GST API Verification**: Validates GSTIN with external GST API and fetches company details
- **Auto-Registration**: Creates user account and vendor profile with extracted data
- **Confirmation Messages**: Step-by-step WhatsApp messages during registration
- **Error Handling**: Clear error messages for invalid images, unclear photos, or failed downloads

### Registration Flow:
1. Unregistered vendor sends GST certificate image to WhatsApp
2. Webhook receives image URL from Gupshup
3. Image downloaded and analyzed via OpenAI Vision
4. AI extracts GSTIN from the certificate
5. GSTIN format validated (regex pattern)
6. GST API called to verify and fetch company details
7. User account and vendor profile created
8. Login credentials sent back via WhatsApp

### GSTIN Pattern:
- Format: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$`
- Example: `27AABCU9603R1ZM` (Maharashtra)
- First 2 digits: State code (01-38)
- Position 13: Always 'Z'

### API Endpoints:
- `POST /api/whatsapp/webhook` - Enhanced to handle image messages for GST extraction

### Files:
- `/app/backend/server.py` - `process_gst_certificate_image` function (lines 9033-9175)
- `/app/backend/server.py` - `process_whatsapp_registration` function (lines 9184-9340)
- `/app/backend/tests/test_gst_certificate_upload.py` - Comprehensive test suite

### Test Report: /app/test_reports/iteration_16.json (100% pass - 40 tests)

### WhatsApp Session Cleanup on User Deletion (Added Mar 7, 2026)
- When a user/vendor is deleted via admin panel, their WhatsApp session is automatically cleaned up
- Helper function `cleanup_whatsapp_session(phone)` handles phone number normalization
- Also cleans up user notifications on deletion
- Logs session removal for audit trail

## Dynamic Machine Parameter Collection via WhatsApp (Added Dec 2025)
WhatsApp machine dimension flow now dynamically asks for category-specific parameters, matching the web app behavior:

### Features:
- **Category-Specific Fields**: Each machine category has its own set of dimension fields (e.g., "thickness" for welding, "spindle diameter" for boring)
- **21 Machine Categories**: Aligned with `/api/machine-categories` endpoint (VMC, HMC, VTL, Lathe, Boring, Grinding, EDM, Welding, etc.)
- **Step Progress**: Shows "Step N/total" during dimension collection for better UX
- **Fuzzy Category Matching**: AI-identified categories are mapped to the correct dimension fields using `get_dimension_config_for_category` helper
- **All Dimension Fields Supported**: Including specialized fields like `laser_power`, `amperage`, `max_temp`, `accuracy`, `layer_thickness`, etc.
- **Bilingual Prompts**: Shows prompts in English + vendor's regional language based on their state location

### Bilingual Language Support (Dec 2025):
The dimension prompts now display in two languages:
1. **English** (primary)
2. **Regional Language** (based on vendor's state)

Supported languages:
- Hindi (Delhi, UP, MP, Bihar, Rajasthan, Haryana, Uttarakhand, Jharkhand, Chhattisgarh, HP)
- Marathi (Maharashtra)
- Gujarati (Gujarat)
- Tamil (Tamil Nadu)
- Telugu (Andhra Pradesh, Telangana)
- Kannada (Karnataka)
- Bengali (West Bengal)
- Punjabi (Punjab)
- Malayalam (Kerala)
- Odia (Odisha)
- Assamese (Assam)

### Key Files:
- `/app/backend/server.py` - STATE_LANGUAGE_MAP (line ~8847)
- `/app/backend/server.py` - DIMENSION_PROMPTS_BILINGUAL (line ~8880)
- `/app/backend/server.py` - `get_bilingual_prompt()` function
- `/app/backend/server.py` - `get_vendor_language()` function

### Dimension Fields by Category Examples:
- **CNC Turning/Lathe**: max_length, max_diameter, max_swing
- **VMC**: max_x, max_y, max_z, table_size_x, table_size_y
- **Boring Machine**: bore_diameter, max_x, max_y, max_z
- **Welding**: max_thickness, max_length, amperage
- **Gear Manufacturing**: max_diameter, max_module, max_length, min_teeth
- **Heat Treatment**: max_x, max_y, max_z, max_temp
- **Inspection/CMM**: max_x, max_y, max_z, accuracy
- **Laser Cutting**: max_x, max_y, max_thickness, laser_power

### Key Files:
- `/app/backend/server.py` - MACHINE_DIMENSION_FIELDS dictionary (line ~8849)
- `/app/backend/server.py` - `get_dimension_config_for_category` helper (line ~9029)
- `/app/backend/server.py` - pending_machines dimension flow (line ~9580)

### Test Report: /app/test_reports/iteration_17.json (100% pass - 27 tests)

## Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions, messages, conversations
- notifications, ratings
