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
- **Auth**: JWT + Custom Google OAuth + 2FA Email OTP
- **Payments**: Stripe (test mode) - planned
- **Email**: Resend API

### Backend Structure (Refactored Mar 23, 2026)
```
/app/backend/
├── app/                    # Modular package
│   ├── config.py           # Settings, constants
│   ├── database.py         # MongoDB connection
│   ├── dependencies.py     # Auth helpers (get_current_user, require_admin)
│   ├── main.py             # FastAPI app factory
│   ├── core/               # Core utilities
│   │   ├── auth.py         # JWT, password hashing
│   │   └── security.py     # Rate limiting, OTP, validation
│   ├── models/             # Pydantic models
│   │   ├── base.py         # UserRole, Status enums
│   │   └── vendor.py       # Vendor models
│   ├── services/           # Business logic
│   │   ├── user_service.py
│   │   ├── vendor_service.py
│   │   ├── notification_service.py
│   │   ├── email_service.py
│   │   └── whatsapp_service.py
│   └── routes/             # API routes (ACTIVE - mounted in server.py)
│       ├── __init__.py     # Router aggregation
│       ├── auth.py         # Auth routes (17 endpoints) ✅ MIGRATED
│       └── users.py        # User profile routes ✅ MIGRATED
├── server.py               # Main entry (~19k lines) - has legacy duplicates marked for removal
├── ARCHITECTURE.md         # Refactoring documentation
└── .env
```

### Google OAuth Deployment Fix (Mar 24, 2026)
- Removed hardcoded `auth.emergentagent.com` fallback from `App.js` `loginWithGoogle`
- Removed hardcoded `preview.emergentagent.com` fallback from `google_auth.py` GET callback
- Removed hardcoded `preview.emergentagent.com` fallback from `config.py` APP_URL
- Added `FRONTEND_URL` env var to backend `.env`
- **Fixed post-login redirect bug (Phase 1)**: Replaced all `process.env.REACT_APP_BACKEND_URL` usages across 10+ files with `window.location.origin`
- **Fixed post-login redirect bug (Phase 2)**: Changed GoogleCallback to use `window.location.href` (full page redirect) instead of React Router `navigate()` — ensures `checkAuth` runs on a clean mount with the stored token. Added defensive retry in ProtectedRoute: if token exists but user is null, re-triggers `checkAuth` instead of redirecting to login.
- **Fixed new Google user registration flow**: Created `/select-role` page for new users with no role. Fixed GoogleCallback to redirect to `/select-role` instead of `/login`. Fixed ProtectedRoute to redirect no-role users to `/select-role` instead of causing redirect loops. Role selection calls `PUT /auth/role` and redirects to the appropriate dashboard.

### Vendor Portfolio Photo Upload & AI Indexing (Mar 25, 2026)
- `POST /api/vendor/portfolio` — Upload JPG/PNG/WEBP, AI analyzes via vision (manufacturing process, material, category, finish, complexity, industry fit, features), stores in `vendor_portfolio` collection
- `GET /api/vendor/portfolio` — Authenticated vendor's portfolio
- `GET /api/vendors/{vendor_id}/portfolio` — Public portfolio view
- `DELETE /api/vendor/portfolio/{portfolio_id}` — Delete portfolio item

### Migration Status (Mar 23, 2026)
- **Phase 1**: Core utilities, models, services - COMPLETE
- **Phase 2**: Route extraction - IN PROGRESS
  - ✅ Auth routes migrated to `/app/routes/auth.py` (17 endpoints)
  - ✅ User profile routes migrated to `/app/routes/users.py` (2 endpoints)
  - ✅ Vendor core routes migrated to `/app/routes/vendor.py` (9 endpoints)
  - ✅ Order routes migrated to `/app/routes/orders.py` (10 endpoints)
  - **Total migrated: ~1,625 lines across 38 endpoints**
  - ⏳ RFQ routes - PENDING (16 endpoints)
  - ⏳ Admin routes - PENDING (83 endpoints - largest section)
  - ⏳ Inspection routes - PENDING
  - ⏳ Quote routes - PENDING

See ARCHITECTURE.md for detailed refactoring plan.

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


### WhatsApp RFQ Notification Fix - Text-Only with Magic Links (FIXED - Mar 15, 2026)
- **Issue**: WhatsApp RFQ notifications with PDF attachments were failing due to:
  - Meta content moderation blocking direct media files as "abusive" (error 368)
  - Template mismatch errors (Gupshup error 4003)
- **Solution**: Changed to text-only notification with secure magic link approach:
  - Vendors receive a well-formatted text message with RFQ details (part name, priority, process, quantity, deadline, match score)
  - Message includes a magic link for instant access (no login needed)
  - Drawings are viewed securely on the platform after clicking the link
- **Technical Changes**:
  - `POST /api/whatsapp/notify-rfq` now sends text-only messages
  - Fixed hardcoded `oemlinker.com` URLs to use `APP_URL` environment variable for preview/production flexibility
  - Magic link redirects vendor directly to `/vendor/rfq/{rfq_id}` page where drawings can be viewed/downloaded

### Magic Link with Redirect for WhatsApp RFQ Access (NEW - Mar 13, 2026)
- **Enhanced Magic Link Generation**: `POST /api/auth/magic-link/generate` now accepts optional `redirect_url` parameter
- **Instant RFQ Access**: When vendors receive RFQ match notifications via WhatsApp, they get a magic link that:
  - Automatically logs them in (no password required)
  - Redirects directly to the specific RFQ page (`/vendor/rfq/{rfq_id}`)
- **Security**: Only internal paths allowed as redirects:
  - `/vendor/`, `/buyer/`, `/admin/`, `/dashboard`, `/rfq/`, `/quotes`, `/orders`
  - External URLs, protocol-relative URLs rejected
- **Extended Expiry**: Magic links for RFQ notifications expire in 30 minutes (increased from 15)
- **WhatsApp Integration Updates**:
  - `rfqs` command now returns magic links for each RFQ and dashboard
  - Individual RFQ detail command includes magic link for quote submission
  - RFQ match notifications include magic links
- **Test Report**: /app/test_reports/iteration_22.json (100% pass - 33/33 tests)

### WhatsApp Logging & Analytics Module (NEW - Mar 13, 2026)
- **Backend Service** (`/app/backend/app/services/whatsapp_logger.py`):
  - Logs all WhatsApp API calls (send_text_message, send_template, send_document, send_image)
  - Tracks: message type, direction, status, phone, error codes, estimated costs
  - MongoDB collection: `whatsapp_logs`
  - Automatic cost estimation based on Gupshup pricing (text: ₹0.35-0.50, media: ₹0.55-0.70)
- **Admin API Endpoints**:
  - `GET /api/whatsapp/logs` - List logs with filters (direction, status, type, phone, date range)
  - `GET /api/whatsapp/logs/stats` - Comprehensive statistics (totals, success rates, costs, breakdowns)
  - `GET /api/whatsapp/logs/errors` - Error summary for last N days
- **Admin Dashboard** (`/admin/whatsapp/logs`):
  - Overview tab: Stats cards, message type breakdown, context breakdown, daily activity
  - Message Logs tab: Filterable log table with pagination
  - Errors tab: Grouped error summary with counts and details
- **Test Report**: /app/test_reports/iteration_23.json (100% pass - 17/17 backend tests)


### User Roles & Permissions Management (NEW - Mar 13, 2026)
- **47 Granular Permissions** across 11 modules:
  - User Management (5), Vendor Management (5), Buyer Management (3)
  - RFQ Management (6), Quote Management (5), Order Management (5)
  - Payments & Finance (4), WhatsApp (4), Analytics (3)
  - Disputes (3), System Admin (4)
- **7 System Roles** (cannot be deleted, but permissions editable):
  - Super Admin (47 perms), Admin (33), Sales Manager (13)
  - Support Agent (10), Finance Admin (8), Vendor (7), Buyer (11)
- **Custom Roles**: Create unlimited custom roles with selected permissions
- **API Endpoints**:
  - `GET /api/admin/permissions` - List all available permissions
  - `GET/POST/PUT/DELETE /api/admin/roles` - Role CRUD operations
  - `POST /api/admin/roles/assign` - Assign role to user
  - `GET /api/user/permissions` - Get current user's permissions
- **Admin UI** (`/admin/roles`):
  - Role cards with color indicators and permission counts
  - Create/Edit dialogs with expandable permission modules
  - User assignment dialog with search
- **Test Report**: /app/test_reports/iteration_24.json (100% pass - 17/17 backend tests)


### Admin User Role Selection in Add/Edit User (NEW - Mar 14, 2026)
- **Backend Enhancement**:
  - `AdminUserCreate` model now includes `custom_role: Optional[str]` field
  - `POST /api/admin/users` endpoint saves `custom_role` when creating users
  - `PUT /api/admin/users/{user_id}` endpoint now allows updating `custom_role`
- **Frontend UI** (`/app/frontend/src/pages/AdminDashboard.jsx`):
  - Add User Dialog: Includes Base Role dropdown (Buyer/Vendor/Admin) and Custom Role dropdown with all system roles
  - Edit User Dialog: Same role selection with current values pre-populated
  - Helper text shows "User will have permissions from both X role and Y role"
  - Custom roles are fetched from `GET /api/admin/roles?include_base_roles=false`
- **Test Report**: /app/test_reports/iteration_26.json (100% pass - 9/9 backend tests, all frontend features verified)


### Permission-Based Sidebar Menu (NEW - Mar 14, 2026)
- **DashboardLayout** (`/app/frontend/src/components/layout/DashboardLayout.jsx`):
  - Sidebar menu now dynamically shows navigation items based on user's role and permissions
  - Users with "None" base role but a custom_role see Staff-specific navigation
  - Admin users see: Admin Panel, Analytics, WhatsApp, WA Logs, Roles, File Manager, Disputes
  - Vendor users see: Dashboard, Matched RFQs, Company Profile, Machines, My Quotes, Disputes, Messages
  - Buyer users see: Dashboard, My RFQs, Received Quotes, New RFQ, Disputes, My Profile, Messages
  - Staff users see permission-filtered items including Admin Panel (if permitted), Analytics, Messages, RFQ-related links
- **Header Portal Name**: Now shows role-specific portal name (e.g., "Sales Manager Portal" for custom roles)
- **User Info**: Shows custom_role name in sidebar when available




### Permission-Based Dashboard Quick Actions (NEW - Mar 14, 2026)
- **usePermissions Hook** (`/app/frontend/src/hooks/usePermissions.js`):
  - Fetches user permissions from `/api/user/permissions`
  - Provides `hasPermission()`, `hasAnyPermission()`, `hasAllPermissions()` helpers
  - Auto-refreshes permissions after login
- **PermittedActions Component** (`/app/frontend/src/components/PermittedActions.jsx`):
  - Displays color-coded action cards filtered by user permissions
  - Shows badge with count of available actions
  - Configurable for different dashboard types
- **Dashboard Integration**:
  - Admin Dashboard: 10 actions (Users, Vendors, RFQs, Analytics, WhatsApp, Files, etc.)
  - Buyer Dashboard: 10 actions (Create RFQ, AI Analysis, Find Vendors, Quotes, Orders, etc.)
  - Vendor Dashboard: 8 actions (Browse RFQs, Quotes, Orders, Machines, Profile, etc.)
- **Test Report**: /app/test_reports/iteration_25.json (100% pass)




### Role-Specific Quick Actions for All User Types (NEW - Mar 14, 2026)
- **Added Dashboard Action Configurations for**:
  - **Sales Manager** (13 actions): Vendor Directory, Buyer Accounts, All RFQs, Create RFQ, Edit RFQs, AI Analysis, Match Vendors, View Quotes, Approve Quotes, Negotiate Deals, View Orders, Create Orders, Sales Analytics
  - **Support Agent** (10 actions): User Lookup, Vendor/Buyer Profiles, RFQ/Quote/Order History, WhatsApp Inbox, Send Messages, Dispute Queue, Resolve Disputes
  - **Finance Admin** (8 actions): Payment Dashboard, Process Payments, Issue Refunds, Financial Reports, Order Overview, Revenue Analytics, Financial Analytics, Export Reports
  - **Regional Manager** (7 actions): Regional Vendors, Edit Vendors, Regional RFQs, Manage RFQs, Regional Quotes, Approve Quotes, Regional Analytics
  - **Supervisor** (8 actions): Team Members, Vendor List, RFQ Queue, Quote Review, Order Status, WhatsApp Messages, Team Disputes, Team Performance
- **Supervisor Role**: Added new system role with 8 permissions
- **Staff Dashboard** (`/staff/dashboard`): New dashboard page for staff with custom roles
- **Additive Permissions**: Users with custom roles get permissions from BOTH their base role AND custom role





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
- Item-wise (per-drawing) vendor quotation system ✓ (Mar 20, 2026)
- Partial quoting feature ✓ (Mar 20, 2026)
- Hybrid Third-Party Inspection System ✓ (Mar 21, 2026)
  - Buyer inspection request from OrderDetail page
  - Basic (Platform Inspector) and Certified (External Agency) types
  - Inspector Dashboard for report submission
  - Admin Inspections Tab for management and assignment
  - Dynamic pricing configuration
- VendorMatchedRFQs "Submit Quote" button redirect fix ✓ (Mar 21, 2026)
  - Now redirects to /vendor/rfq/{rfq_id} for full RFQ details before quoting
- Orders menu added to Buyer and Vendor sidebars ✓ (Mar 21, 2026)
  - Created BuyerOrders.jsx and VendorOrders.jsx pages
  - Added /buyer/orders and /vendor/orders routes
  - Added backend APIs for enriched order lists
- Vendor Inspector Assignment feature ✓ (Mar 21, 2026)
  - Vendors can now assign inspectors to orders they own
  - Added /vendor/orders/{order_id}/assign-inspector API
  - Added /vendor/inspectors API to list available inspectors
  - Updated InspectionStatusCard with vendor assign inspector modal
  - Fixed inspection authorization for vendors
- Vendor Inspection Scheduling (REPLACED inspector assignment) ✓ (Mar 21, 2026)
  - Vendors can schedule inspection date/time for buyer-requested inspections
  - Vendors CANNOT assign inspectors (admin-only)
  - Added /vendor/orders/{order_id}/schedule-inspection API
  - Vendor can add notes for inspector (access details, contact info)
  - Inspection assignment remains admin-only

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

### Inspection System APIs (Added Mar 21, 2026)
- GET /api/inspection/pricing - Get inspection pricing (Basic/Certified)
- POST /api/orders/{order_id}/request-inspection - Buyer requests inspection
- POST /api/inspections/{inspection_id}/pay - Pay inspection fee (MOCKED)
- GET /api/orders/{order_id}/inspection - Get inspection for order
- POST /api/inspector/orders/{order_id}/report - Inspector submits report
- POST /api/inspections/{inspection_id}/approve - Buyer approves/rejects
- GET /api/admin/inspections - List all inspections (admin)
- GET /api/admin/inspectors - List inspectors (admin)
- POST /api/admin/orders/{order_id}/assign-inspector - Assign inspector (admin)
- POST /api/admin/inspectors/create - Create inspector (admin)
- GET /api/admin/inspection-pricing - Get pricing config (admin)
- POST /api/admin/inspection-pricing - Set pricing (admin)

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
The WhatsApp flows now display messages in two languages:
1. **English** (primary)
2. **Regional Language** (based on vendor's state)

**Supported Languages:** Hindi, Marathi, Gujarati, Tamil, Telugu, Kannada, Bengali, Punjabi, Malayalam, Odia, Assamese

**Bilingual Messages Applied To:**
- Welcome messages
- Help/Menu commands
- Registration flow (GST found, confirmation, success)
- Machine identification and dimension prompts
- Machine saved confirmation
- Profile command
- Machines list command
- Error messages

**Key Functions:**
- `get_vendor_language(vendor)` - Detects language from vendor's state
- `get_bilingual_message(key, vendor)` - Returns regional translation
- `get_bilingual_prompt(field_key, english_prompt, vendor)` - Formats dimension prompts
- `WHATSAPP_MESSAGES_BILINGUAL` - Dictionary with all translations

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

## Buyer-Facing Vendor Machine Photos & Details (NEW - Mar 9, 2026)

### Feature Overview
Buyers can now view complete machine details including photos when viewing a vendor's profile. This helps buyers make informed decisions about which vendors to work with.

### Implementation Details:
**Frontend**: `/app/frontend/src/pages/VendorProfileView.jsx`
- Enhanced machine cards with photo display
- Full-screen image gallery modal with navigation
- Dynamic dimension display based on machine category
- Availability status badges (Available, Engaged, Maintenance, Offline)
- Materials supported with colored badges

**Backend**: `/api/vendors/{vendor_id}/full` endpoint
- Returns all machines with images array
- Already includes all dimension fields

### Machine Display Features:
1. **Machine Photos**:
   - Main image with hover zoom effect
   - Thumbnail gallery for multiple images
   - "No photos available" placeholder when no images
   - Full-screen gallery modal with prev/next navigation

2. **Dynamic Dimensions** (based on machine category):
   - CNC Turning/Lathe: max_diameter, max_length, max_swing
   - VMC/HMC: Work Envelope (XYZ), table_size
   - Boring: bore_diameter, spindle_bore, spindle_travel
   - Sheet Metal: tonnage, max_thickness, laser_power
   - Welding: amperage, max_thickness
   - Heat Treatment: max_temp
   - Inspection/CMM: accuracy
   - 5-Axis: A-axis range, C-axis range

3. **Availability Status**:
   - Available (green badge)
   - Engaged (amber badge)
   - Maintenance (slate badge)
   - Offline (red badge)

4. **Materials Supported**: Emerald green badges showing all materials

### Test Report: /app/test_reports/iteration_18.json (100% pass - frontend verified)

## WhatsApp Email Reminder Feature (NEW - Mar 9, 2026)

### Feature Overview
WhatsApp-registered vendors now receive periodic reminders to add their email address. Email is important for receiving RFQ match notifications, quotation updates, and platform alerts.

### Implementation Details:
**Location**: `/app/backend/server.py`
- `EMAIL_REMINDER_MESSAGES` - Bilingual messages for 8 Indian languages
- `EMAIL_REMINDER_INTERVAL_HOURS = 24` - Reminder sent every 24 hours
- `check_and_send_email_reminder()` - Checks if vendor needs reminder
- `process_email_input()` - Validates and saves email
- `pending_email_inputs` - Tracks pending email input state (10 min expiry)

### WhatsApp Commands:
- **`email`** - Add/update email address (supports regional language variants)
- Email prompts appear in registration success message
- Help menu includes email command

### Email Validation:
- Format validation using regex
- Duplicate email check (prevents using another user's email)
- 10-minute window to provide email after typing "email" command

### Bilingual Support:
Regional languages supported: Hindi, Marathi, Gujarati, Tamil, Telugu, Kannada, Bengali, Punjabi

### Test Report: /app/test_reports/iteration_19.json (100% pass - 20 backend tests)

## Vendor Profile Email Field (NEW - Mar 10, 2026)

### Feature Overview
Added email field to vendor profile page on the web app. Email syncs correctly whether updated via WhatsApp or web app.

### Implementation:
**Frontend**: `/app/frontend/src/pages/VendorProfile.jsx`
- Added `contact_email` field to form state
- Email input with `data-testid="email-input"`
- Placeholder: "contact@yourcompany.com"
- Helper text: "For RFQ notifications & updates"

**Backend**: `/app/backend/server.py`
- Added `contact_email` field to `VendorProfileCreate` model (line 717)
- `update_vendor_profile` endpoint syncs email correctly:
  - Always saves `contact_email` to vendor record
  - For WhatsApp users (phone-based email): also updates `user.email` for login
  - For regular users: only updates `contact_email`, login email unchanged

### Test Report: /app/backend/tests/test_vendor_profile_email.py (8 tests passed)

## Phone Login Preservation Bug Fix (Mar 10, 2026)

### Issue
Phone number login was breaking after vendors updated their email via web app or WhatsApp.

### Root Cause
The `update_vendor_profile` endpoint was overwriting the `email` field (which stores phone number for WhatsApp users) with the new `contact_email`.

### Fix Applied:
1. **VendorProfile model**: Added `contact_email` field to response model
2. **update_vendor_profile endpoint**: 
   - Never changes `email` field for users with `phone_login=True`
   - Only updates `contact_email` field for notifications
3. **WhatsApp email update flow**: 
   - Same fix - preserves phone number in `email` field
   - Only updates `contact_email` for notifications

### Test Report: /app/backend/tests/test_phone_login_preservation.py (2 tests passed)

## WhatsApp Message Management System (NEW - Mar 10, 2026)

### Feature Overview
Admin dashboard to view WhatsApp conversations and send messages/broadcasts to vendors.

### Backend Implementation (`/app/backend/server.py`):
**New Endpoints:**
- `GET /api/admin/whatsapp/conversations` - List all conversations with pagination and search
- `GET /api/admin/whatsapp/conversations/{phone}` - Get messages for a specific phone
- `POST /api/admin/whatsapp/send` - Send a message to a phone number
- `POST /api/admin/whatsapp/broadcast` - Send bulk messages to multiple numbers
- `GET /api/admin/whatsapp/stats` - Get messaging statistics
- `POST /api/admin/whatsapp/grant-access/{user_id}` - Grant WhatsApp admin access to a user
- `POST /api/admin/whatsapp/revoke-access/{user_id}` - Revoke access
- `GET /api/admin/whatsapp/users-with-access` - List users with WhatsApp admin access

**Message Storage:**
- `store_whatsapp_message()` function stores all incoming/outgoing messages
- Messages stored in `whatsapp_messages` collection
- Tracks: phone, direction, type, content, vendor_id, vendor_name, read status

**Access Control:**
- Admin users have access by default
- Other users need `whatsapp_admin: true` flag on their user record

### Frontend Implementation:
**Files:**
- `/app/frontend/src/pages/WhatsAppInbox.jsx` - Full inbox UI with conversations and messaging
- `/app/frontend/src/pages/WhatsAppAdmin.jsx` - Updated with "Open Inbox" button

**Features:**
- Conversation list with search
- Real-time chat view with message history
- Send text messages to vendors
- Broadcast messages to multiple vendors
- Stats dashboard (total messages, incoming, outgoing, unread)
- Mark messages as read when viewed

**Routes:**
- `/admin/whatsapp` - Integration settings and testing
- `/admin/whatsapp/inbox` - Message inbox (new)

### Database Schema:
**whatsapp_messages collection:**
```json
{
  "message_id": "msg_xxx",
  "phone": "+919876543210",
  "phone_normalized": "9876543210",
  "direction": "incoming|outgoing",
  "message_type": "text|image|audio|template",
  "content": "message text",
  "vendor_id": "vendor_xxx",
  "vendor_name": "Company Name",
  "template_name": null,
  "sent_by": "user_id (for outgoing)",
  "read": true|false,
  "created_at": "ISO timestamp"
}
```

## Meta Data Deletion Policy Compliance (NEW - Mar 11, 2026)

### Feature Overview
Meta (WhatsApp Business API) compliant data deletion system. Required for WhatsApp Business Platform compliance.

### Implementation Details:

**Frontend Pages:**
- `/privacy-policy` - Comprehensive privacy policy with WhatsApp data handling info
- `/data-deletion` - Data deletion request form + status check
- `/data-deletion-status` - Status check page (accessed via URL with code param)

**Backend Endpoints:**
- `POST /api/data-deletion/request` - Submit deletion request (phone or email)
- `GET /api/data-deletion/status/{code}` - Check deletion status
- `POST /api/meta/data-deletion-callback` - Meta callback endpoint (returns URL + confirmation_code)
- `POST /api/admin/data-deletion/process/{code}` - Admin endpoint to process deletion
- `GET /api/admin/data-deletion/requests` - Admin endpoint to list all requests

**Footer Links (LandingPage.jsx):**
- Terms of Service
- Privacy Policy
- Data Deletion
- Contact

**Data Deletion Flow:**
1. User submits request with phone number or email
2. System generates confirmation code (DEL_XXXXXXXXXXXX)
3. Request stored in `data_deletion_requests` collection with status "pending"
4. User receives confirmation code to track status
5. Admin can process deletion via admin endpoint
6. Status updates to "in_progress" then "completed"

**Meta Callback Format:**
```json
{
  "url": "https://oemlinker.com/data-deletion-status?code=DEL_xxx",
  "confirmation_code": "DEL_xxx"
}
```

**Database Collection (data_deletion_requests):**
```json
{
  "confirmation_code": "DEL_xxx",
  "phone": "9876543210",
  "email": "user@example.com",
  "reason": "User provided reason",
  "status": "pending|in_progress|completed|failed",
  "requested_at": "ISO timestamp",
  "processed_at": "ISO timestamp",
  "completed_at": "ISO timestamp"
}
```

### Test Report: /app/test_reports/iteration_20.json (100% pass - 28 tests)

## Magic Link Login Feature (Fixed - Dec 2025)

### Feature Overview
WhatsApp-registered vendors can log into the web app without a password using a magic link sent via WhatsApp.

### Implementation Details:

**Flow:**
1. Vendor sends "login" command to WhatsApp bot
2. Backend generates a single-use token (15-minute expiry)
3. Magic link URL sent to vendor via WhatsApp
4. Vendor clicks link → redirected to `/magic-login?token=xxx`
5. Frontend verifies token via API
6. On success, JWT token stored and user redirected to dashboard

**Bug Fix Applied:**
- Issue: React StrictMode double `useEffect` invocation was invalidating the single-use token
- Solution: Used `useRef` to track verification state that persists across re-renders
- Changed from `login()` (makes POST request) to `updateUser()` (state update only)
- Added `isMounted` ref to prevent state updates on unmounted component

**Backend Endpoints:**
- `POST /api/auth/magic-link/generate?phone=xxx` - Generate token for a phone number
- `GET /api/auth/magic-link/verify/{token}` - Verify token and return JWT

**Frontend:**
- `/app/frontend/src/pages/MagicLogin.jsx` - Magic login page component

### Test Report: /app/backend/tests/test_magic_link.py (12 tests passed)

## WhatsApp Approved Templates Display (Updated - Dec 2025)

### Feature Overview
Admin can view and send pre-approved WhatsApp message templates from the admin dashboard. Templates are now fetched **live from Gupshup API** instead of hardcoded.

### Implementation Details:

**Backend (`/app/backend/app/services/whatsapp_service.py`):**
- `get_templates()` method tries multiple Gupshup API endpoints to fetch templates
- Supports Partner API, WA App Template API, and fallback endpoints
- Normalizes template format from different API responses
- Filters for APPROVED/ACTIVE/ENABLED templates

**Backend Endpoints:**
- `GET /api/whatsapp/templates` - Fetch all approved templates from Gupshup
- `POST /api/whatsapp/send-template` - Send a template via Gupshup Template API

**Frontend (`/app/frontend/src/pages/WhatsAppAdmin.jsx`):**
- "Approved WhatsApp Templates" section with live/fallback indicator
- Displays: template name, ID, status badge, category, language
- Template content in code block with copy button
- Parameter input field for template variables
- Send button to dispatch template to entered phone number

**Environment Variables Required:**
```
GUPSHUP_APP_NAME=OEMLinker
GUPSHUP_API_KEY=sk_xxx
GUPSHUP_SOURCE_NUMBER=919831509919
GUPSHUP_APP_ID=escrow-payments-2  # Required for live templates
```

**Template Response Format:**
```json
{
  "templates": [
    {
      "id": "uuid",
      "name": "template_name",
      "status": "APPROVED",
      "category": "UTILITY|MARKETING|AUTHENTICATION",
      "language": "en",
      "content": "Template body with {{1}} placeholders",
      "header": null,
      "footer": null,
      "buttons": []
    }
  ],
  "total": 3,
  "source": "gupshup_wa_app_template"
}
```

## RFQ Distribution & Advanced Quotation System (Implemented Mar 20, 2026)

### Overview
AI-powered RFQ analysis with intelligent vendor matching and enhanced quotation system with cost breakdown.

### AI-Based RFQ Analysis:
- **Process Detection**: Analyzes RFQ text and AI analysis for keywords (casting, forging, machining, fabrication)
- **detect_process_requirements()**: Returns primary_process, all_processes, raw_material_provided, material_type
- **Keywords**: casting (cast, foundry, mould), forging (forge, hot working), machining (CNC, turning, milling), fabrication (welding, sheet metal)

### Vendor Matching Engine:
- **evaluate_vendor_match()**: Matches vendors based on machine categories
- **Process-to-Category Mapping**: Maps detected processes to required machine categories
- **Exclusion Logic**: When raw material is provided by buyer, casting/forging vendors are excluded
- **Scoring**: Base score 50, +10 per matching capability, capped at 100

### Enhanced Quotation System:
**Quote Fields:**
- `material_provided_by_buyer` (boolean)
- `material_cost` (required if vendor provides material)
- `machining_cost` (always required)
- `additional_costs` (dict: e.g., {"heat_treatment": 2000, "surface_finish": 1500})
- `total_cost` (auto-calculated: material + machining + additional)
- `cost_breakdown_remarks`

**Validation:**
- machining_cost > 0 required
- material_cost > 0 required when material_provided_by_buyer = false

### Backend Endpoints:
- `POST /api/rfq/analyze-and-match` - AI process detection + vendor matching
- `GET /api/rfq/{rfqId}/vendors` - Get matched vendors with quote status
- `GET /api/rfq/{rfqId}/quotations` - Get quotations with cost breakdown comparison
- `POST /api/vendor/quotation` - Submit quotation with cost breakdown

### Frontend Components:
- **QuotationComparison**: Table view with columns: Vendor, Material, Machining, Additional, Total, Lead Time, Actions
- **VendorQuotationForm**: Form with material toggle, cost breakdown fields, total calculation
- **RFQ Details Dialog**: Shows quotes with cost breakdown, "Compare All Quotations" button, "AI Analyze & Match" button

### Comparison Summary:
```json
{
  "lowest_total_cost": 1500,
  "lowest_machining_cost": 1500,
  "average_total_cost": 14250,
  "quotes_with_material": 1,
  "quotes_without_material": 1
}
```

### Test Report: /app/test_reports/iteration_31.json (100% pass - 23 backend tests + full UI verification)

## Item-wise Vendor Quotation System (Implemented Mar 20, 2026)

### Overview
Enhanced the quotation system to support item-wise (per drawing) quotations for multi-part RFQs. Vendors can now quote each drawing/item separately with individual cost breakdowns.

### Features:
- **Item-wise Mode**: Automatically activates when RFQ has multiple drawings
- **Per-item Cost Breakdown**: Each item has material cost, labour cost, and additional costs
- **Material Toggle per Item**: Buyer-provided material can be specified per item
- **Expandable Item Cards**: UI shows collapsible cards for each item
- **Grand Total Calculation**: Automatic sum of all item costs

### Backend Endpoints:
- `POST /api/vendor/quotation/itemwise` - Submit item-wise quotation with items array
- `GET /api/rfqs/{rfq_id}/items` - Get RFQ drawings/items for quoting
- `GET /api/rfq/{rfq_id}/quotations` - Enhanced to include is_itemwise flag and items array

### Data Model (QuoteItem):
```json
{
  "item_id": "drawing_abc123",
  "drawing_id": "drawing_abc123",
  "title": "Shaft Component A",
  "material_provided_by_buyer": false,
  "material_cost": 5000,
  "labour_cost": 3000,
  "additional_costs": {"heat_treatment": 500},
  "total_cost": 8500,
  "remarks": "Premium steel used"
}
```

### Quote Response (is_itemwise: true):
```json
{
  "quote_id": "quote_xxx",
  "rfq_id": "rfq_yyy",
  "is_itemwise": true,
  "items": [...],
  "total_cost": 26000,
  "items_count": 3,
  "comparison_summary": {
    "itemwise_quotes": 2,
    "flat_quotes": 1
  }
}
```

### Frontend Components Updated:
- **VendorQuotationForm.jsx**: Fetches items from API, displays expandable form per drawing, auto-switches to item-wise mode
- **QuotationComparison.jsx**: Shows "item-wise" badge, expandable item breakdown in comparison table
- **QuoteDetailModal.jsx**: Displays item-wise cost breakdown when viewing quote details
- **RFQDetail.jsx**: Uses VendorQuotationForm in Submit Quote dialog

### Test Report: /app/test_reports/iteration_32.json (100% backend, 90% frontend)

## Partial Quoting Feature (Implemented Mar 21, 2026)

### Overview
Vendors can now submit quotations for only selected items/drawings from a multi-part RFQ, instead of being required to quote all items.

### Features:
- **Item Selection**: Checkboxes to select which items to quote
- **Select All / Deselect All**: Quick selection buttons
- **Quote Status Indicator**: Shows "No items selected" (red), "Partial Quote: X of Y items" (amber), "Full Quote" (green)
- **Partial Badge in Comparison**: Shows "Partial (2/4)" badge in quotation comparison

### Backend Changes:
- `POST /api/vendor/quotation/itemwise` now accepts partial items array
- Response includes: `is_partial`, `quoted_items_count`, `total_rfq_items`, `quoted_item_ids`
- `GET /api/rfq/{rfq_id}/quotations` includes `partial_quotes` count in comparison_summary

### Data Model (Quote with Partial):
```json
{
  "quote_id": "quote_xxx",
  "is_partial": true,
  "quoted_items_count": 2,
  "total_rfq_items": 4,
  "quoted_item_ids": ["drawing_abc", "drawing_def"],
  "items": [...]
}
```

### Frontend Components Updated:
- **VendorQuotationForm.jsx**: Item selection checkboxes, Select All/Deselect All buttons, status indicator
- **QuotationComparison.jsx**: AlertTriangle icon and "Partial (X/Y)" badge for partial quotes

### Test Report: /app/test_reports/iteration_33.json (100% backend, 85% frontend)

## RFQ Drawing Access & PDF Layout Fix (Implemented Mar 19, 2026)

### Overview
Fixed drawing access to use direct S3 presigned URLs and improved PDF generation with professional layout.

### Drawing Access Fixes:
- **Presigned S3 URLs**: Drawings now use `get_presigned_url()` for fresh S3 URLs (1 hour for API, 24 hours for PDF)
- **Multiple URL fields**: Each drawing has `file_url`, `view_url`, `download_url`
- **File type detection**: `is_previewable`, `is_image`, `is_pdf` flags added
- **Preview support**: Images show inline preview, PDFs show iframe preview
- **View/Download buttons**: Separate buttons - View opens in new tab, Download triggers file download

### PDF Layout Improvements:
- **Page numbers**: Footer shows "Page X" with generation timestamp
- **OEMLinker branding**: Header with logo and "REQUEST FOR QUOTATION" title
- **RFQ Info Bar**: Orange-bordered bar with Date, Status, Material
- **Structured sections** with HRFlowable dividers:
  - Buyer Details (Name, Company, Email, Phone, Location)
  - RFQ Details (Part Name, Quantity, Tolerance, Surface Finish, Deadline, Delivery)
  - Description/Specifications (wrapped text in bordered box)
  - Technical Analysis (blue background, AI recommendations)
  - Attachments (numbered list with download links)
- **Text wrapping**: Long text properly wraps within table cells
- **A4 format**: 15mm margins, professional typography

### Test Report: /app/test_reports/iteration_30.json (100% pass - 20 backend tests + full UI verification)

## Admin RFQ Details View & PDF Download (Implemented Mar 19, 2026)

### Overview
Admin users and permitted staff can view full RFQ details and download RFQs as professionally formatted PDFs.

### Features:
- **View Button (Eye icon)** in RFQs tab Actions column
- **RFQ Details Dialog** with comprehensive information:
  - Header: RFQ ID, Status, Created date
  - Buyer Details: Name, Company, Email, Phone, Location
  - RFQ Information: Part Name, Material, Quantity, Tolerance, Surface Finish, Deadline, Delivery Location
  - Description/Specifications
  - Technical Analysis (AI): Recommended Processes, Dimensions, Part Geometry, Complexity Score
  - Attachments/Drawings with download links
  - Matched Vendors list
  - Quotes Received with vendor info and pricing
- **Download PDF Button** generates A4 PDF with:
  - OEMLinker branding header
  - RFQ ID bar with status and date
  - Buyer details section
  - RFQ details section
  - Technical specifications
  - Attachments list with links
  - Professional footer

### Backend Endpoints:
- `GET /api/admin/rfqs/{rfqId}` - Enhanced to return buyer_info, drawings, quotes, matched_vendors_details, ai_summary
- `GET /api/admin/rfqs/{rfqId}/pdf` - Generates PDF using reportlab, returns as downloadable file

### Test Report: /app/test_reports/iteration_29.json (100% pass - 18 backend tests + full UI verification)

## Admin RFQ-Vendor Manual Matching (Implemented Mar 19, 2026)

### Overview
Admin users and permitted staff can manually match RFQs to one or more vendors and notify both parties.

### Features:
- **Match Vendors Button** in RFQs tab - opens dialog to search and select vendors
- **Vendor Search Dialog** with search by name, filter by capability/category
- **Multi-select** - match multiple vendors at once
- **Already Matched Badge** - shows vendors already matched to avoid duplicates
- **View Matches** - click on vendor count to see all matched vendors with status
- **Remove Match** - unmatch vendors from RFQ
- **Notifications** - sends WhatsApp (if configured), email, and in-app notifications to vendors and buyer
- **Activity Logging** - tracks all match/unmatch actions with user info

### Backend Endpoints:
- `POST /api/admin/rfq/{rfqId}/match-vendors` - Match vendors to RFQ
- `GET /api/admin/rfq/{rfqId}/matches` - Get all matched vendors with status
- `DELETE /api/admin/rfq/{rfqId}/match/{vendorId}` - Remove vendor match
- `PUT /api/admin/rfq/{rfqId}/match/{vendorId}/status` - Update match status
- `GET /api/admin/vendors/search` - Search vendors for matching (with machine info)

### Database Schema (rfq_vendor_matches):
```json
{
  "match_id": "match_xxx",
  "rfq_id": "rfq_xxx",
  "vendor_id": "vendor_xxx",
  "matched_by": "admin_001",
  "matched_by_name": "Admin User",
  "status": "matched|viewed|responded|quoted",
  "match_type": "manual|auto",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

### RBAC Permissions:
- `rfqs.match_vendors` - Required for matching/unmatching vendors

### Notifications Sent:
- **Vendor**: WhatsApp message with magic link, email with RFQ details, in-app notification
- **Buyer**: Email confirming X vendors matched, in-app notification

### Test Report: /app/test_reports/iteration_28.json (100% pass - 21 backend tests + full UI verification)

## Admin Machine Management (Implemented Mar 19, 2026)

### Overview
Admin users and permitted staff can create, edit, and delete machines for any vendor directly from the Admin Dashboard.

### Features:
- **Machines Tab** in Admin Dashboard with "Add Machine" button
- **Create Machine Dialog** with vendor selection, category-based form fields
- **Activity Logging** for all machine CRUD operations
- **Max 5 images per machine** limit enforced
- **RBAC Permissions**: `machines.view`, `machines.create`, `machines.edit`, `machines.delete`, `machines.manage_images`

### Backend Endpoints:
- `GET /api/admin/machines` - List all machines (optional vendor_id filter)
- `POST /api/admin/machines` - Create machine with activity log
- `GET /api/admin/machines/{id}` - Get machine details
- `PUT /api/admin/machines/{id}` - Update machine with activity log
- `DELETE /api/admin/machines/{id}` - Delete machine with activity log
- `POST /api/admin/machines/{id}/images` - Upload machine image (max 5)
- `DELETE /api/admin/machines/{id}/images` - Delete machine image
- `GET /api/admin/activity-logs` - General activity logs
- `GET /api/admin/activity-logs/machines` - Machine-specific activity logs

### Machine Fields:
- `vendor_id` (required), `name`, `machine_category` (required), `machine_type`
- `brand`, `model`, `tolerance`, `materials`
- Category-specific dimension fields (max_x, max_y, max_z, max_diameter, etc.)
- `created_by`, `created_at`, `updated_by`, `updated_at`
- `images` (array of S3 presigned URLs, max 5)

### Activity Log Schema:
```json
{
  "activity_id": "act_xxx",
  "type": "machine_created|machine_updated|machine_deleted",
  "action": "create|update|delete",
  "entity_type": "machine",
  "entity_id": "machine_xxx",
  "vendor_id": "vendor_xxx",
  "user_id": "admin_001",
  "user_name": "Admin User",
  "details": {
    "machine_name": "...",
    "machine_category": "...",
    "vendor_name": "...",
    "updated_fields": []  // For updates only
  },
  "created_at": "ISO timestamp"
}
```

### Test Report: /app/test_reports/iteration_27.json (100% pass - 17 backend tests)

## Database Collections
- users, user_sessions, vendors, machines
- rfqs, drawings, quotes, orders
- payment_transactions, messages, conversations
- notifications, ratings
- data_deletion_requests
- magic_link_tokens (for magic link auth)
- **activity_logs** (NEW - for machine and other activity tracking)



## AWS S3 Cloud Storage (Implemented Mar 13, 2026)

### Overview
All file uploads (machine images, RFQ drawings) are now stored in AWS S3 for persistent storage across deployments.

### Configuration
```env
AWS_ACCESS_KEY_ID=<user-provided>
AWS_SECRET_ACCESS_KEY=<user-provided>
AWS_S3_BUCKET_NAME=oemlinker-storage
AWS_REGION=ap-south-1
```

### Storage Service
File: `/app/backend/app/services/s3_storage_service.py`

**Functions:**
- `upload_file(data, filename, folder, content_type)` - Upload file to S3
- `download_file(path)` - Download file from S3
- `delete_file(path)` - Delete file from S3
- `list_files(prefix)` - List files with optional prefix filter
- `get_presigned_url(path, expiration)` - Generate temporary access URL
- `upload_machine_image(image_data, filename, vendor_id)` - Upload machine image
- `upload_drawing(drawing_data, filename, rfq_id)` - Upload RFQ drawing

### File Storage Structure
```
s3://oemlinker-storage/
├── machines/
│   └── {vendor_id}/
│       └── {uuid}.{ext}    # Machine images
└── drawings/
    └── {rfq_id}/
        └── {uuid}.{ext}    # RFQ drawings
```

### Admin File Manager
Route: `/admin/files`
File: `/app/frontend/src/pages/FileManager.jsx`

**Features:**
- View storage statistics (total files, machine images, drawings, total size)
- Browse files with search and filter (All/Machines/Drawings)
- View files directly from S3
- Delete files from S3 (admin only)

### API Endpoints
- `GET /api/admin/files?prefix=` - List files (admin only)
- `GET /api/admin/files/stats` - Get storage statistics (admin only)
- `DELETE /api/admin/files/{path}` - Delete file (admin only)
- `GET /api/storage/{path}` - Serve file from S3 (authenticated)

### Migration Notes
- Machine images uploaded via web or WhatsApp now go directly to S3
- Drawing uploads store files in S3 with metadata in MongoDB
- Legacy drawings (stored as base64 in MongoDB) are still supported
- Local filesystem (`/app/uploads/`) is deprecated but legacy files are still served



## NDA Enforcement for RFQ Drawings (Implemented Mar 23, 2026)

### Overview
IP Protection feature allowing buyers to enforce Non-Disclosure Agreements (NDAs) on their RFQ drawings. Vendors must accept the NDA before they can view or download any protected drawings.

### Features
- **Buyer Controls**: Toggle "Require NDA for Drawings" when creating RFQs
- **Vendor Flow**: NDA modal appears before accessing protected drawings
- **Admin Management**: NDA Templates tab in Admin Dashboard for template CRUD
- **Audit Trail**: Captures vendor IP address and User-Agent when accepting NDAs

### Database Collections

**nda_templates**
```json
{
  "nda_id": "nda_{uuid}",
  "title": "Standard NDA Template",
  "content": "<html content>",
  "version": "1.0",
  "is_default": true,
  "created_at": "ISO timestamp",
  "created_by": "admin"
}
```

**nda_acceptances**
```json
{
  "acceptance_id": "nda_acc_{uuid}",
  "vendor_id": "vendor_{id}",
  "rfq_id": "rfq_{id}",
  "nda_id": "nda_{id}",
  "nda_version": "1.0",
  "vendor_name": "Company Name",
  "vendor_email": "vendor@email.com",
  "accepted_at": "ISO timestamp",
  "ip_address": "10.64.132.199",
  "user_agent": "Mozilla/5.0 ..."
}
```

**rfqs (additions)**
- `require_nda: boolean` - Whether NDA is required for this RFQ
- `nda_id: string` - Reference to specific NDA template (optional)

### API Endpoints

**NDA Management (Admin)**
- `GET /api/admin/nda-templates` - List all NDA templates
- `POST /api/admin/nda-templates` - Create new template
- `PUT /api/admin/nda-templates/{nda_id}` - Update template
- `DELETE /api/admin/nda-templates/{nda_id}` - Delete template

**NDA Acceptance (Vendor)**
- `GET /api/rfqs/{rfq_id}/nda` - Get NDA details and acceptance status
- `POST /api/rfqs/{rfq_id}/accept-nda` - Accept NDA (captures IP + User-Agent)
- `GET /api/rfqs/{rfq_id}/nda-acceptances` - List vendors who accepted (buyer/admin)

**Protected Drawing Access**
- `GET /api/drawings/{drawing_id}/view` - View drawing (403 if NDA not accepted)
- `GET /api/drawings/{drawing_id}/download` - Download drawing (403 if NDA not accepted)

### Security Model
- **Backend Enforcement**: Drawing view/download endpoints check NDA acceptance before serving files
- **Bypass Rules**: Admins, staff, and RFQ owners (buyers) bypass NDA checks
- **Audit**: Full tracking of who accepted what NDA, when, from where

### Frontend Components
- `NDAModal.jsx` - Modal displaying NDA terms with acceptance checkbox
- `NDATemplatesTab.jsx` - Admin component for managing NDA templates
- `CreateRFQ.jsx` - Updated with "IP Protection" section and NDA toggle
- `RFQDetail.jsx` - Updated to show NDA banner and modal for vendors

### Test Report
`/app/test_reports/iteration_35.json` - Backend 100% (13/13), Frontend 85%
